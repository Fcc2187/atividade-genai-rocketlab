from datetime import date
import os
import unittest
from unittest.mock import AsyncMock, patch
from tests.helpers import prepare_database
from tests.test_observability import capture_events, events
from app import main


class HTTPTests(unittest.TestCase):
    def setUp(self):
        prepare_database(self)
        self.main = main
        self.env = patch.dict(
            os.environ,
            {
                "DATABASE_PATH": str(self.path),
                "MODEL_PROVIDER": "groq",
                "MODEL_BASE_URL": "https://api.groq.com/openai/v1",
                "MODEL_NAME": "openai/gpt-oss-120b",
                "QUESTION_TIMEOUT_SECONDS": "600",
                "GROQ_API_KEY": "gsk-test",
                "LOG_LEVEL": "DEBUG",
            },
        )
        self.env.start()
        self.addCleanup(self.env.stop)

    def client(self):
        from fastapi.testclient import TestClient

        return TestClient(self.main.app)

    def test_entrada_e_health_sem_modelo(self):
        with (
            patch("app.main.responder", new_callable=AsyncMock) as respond,
            self.client() as client,
        ):
            self.assertEqual(
                client.get("/health").json(), {"status": "ok", "banco": "disponivel"}
            )
            self.assertEqual(client.get("/docs").status_code, 200)
            for body in [
                {},
                {"pergunta": ""},
                {"pergunta": "   "},
                {"pergunta": "x" * 2001},
                {"pergunta": 7},
            ]:
                with self.subTest(body=str(body)[:80]):
                    self.assertEqual(
                        client.post("/perguntas", json=body).status_code, 422
                    )
            respond.assert_not_called()

    def test_resposta_tem_evidencias_reais(self):
        from app.agent import AgentAnswer, QuestionResult

        evidence = self.db.execute_readonly(
            self.path, "SELECT COUNT(*) AS filmes FROM dim_movies", {}
        )
        result = QuestionResult(
            AgentAnswer(status="resultado", resposta="Há dois filmes.", avisos=[]),
            [evidence],
            "openai/gpt-oss-120b",
            {
                "chamadas": 2,
                "tokens_entrada": None,
                "tokens_saida": None,
                "tentativas_sql": 1,
            },
        )
        with (
            capture_events() as stream,
            patch(
                "app.main.responder", new_callable=AsyncMock, return_value=result
            ) as respond,
            self.client() as client,
        ):
            response = client.post(
                "/perguntas", json={"pergunta": "  Quantos filmes?  "}
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["consultas"][0]["linhas"], [[2]])
            self.assertEqual(response.json()["uso"]["tentativas_sql"], 1)
            args = respond.call_args.args
            self.assertEqual(args[0], "Quantos filmes?")
            self.assertEqual(args[2], date.today())
            request_id = response.headers.get("X-Request-ID")
            self.assertTrue(request_id)
            rows = [r for r in events(stream) if r["request_id"] == request_id]
            self.assertEqual(
                [r["event"] for r in rows],
                ["request_started", "question_received", "request_completed"],
            )
            self.assertEqual(rows[1]["question_chars"], 15)
            self.assertEqual(rows[-1]["response_status"], "resultado")
            self.assertIsNone(rows[-1]["tokens_entrada"])
            self.assertEqual(rows[-1]["chamadas"], 2)
            self.assertNotIn("Quantos filmes", stream.getvalue())

    def test_erros_http_sem_detalhes_sensiveis(self):
        from app.agent import (
            ProviderRateLimited,
            ProviderUnavailable,
            InvalidAgentResult,
            QuestionTimedOut,
            ProviderRequestTooLarge,
        )

        for error, code, status in [
            (ProviderUnavailable, "modelo_indisponivel", 503),
            (self.db.DatabaseUnavailable, "banco_indisponivel", 503),
            (InvalidAgentResult, "resposta_invalida", 502),
            (QuestionTimedOut, "prazo_excedido", 504),
            (ProviderRateLimited, "cota_excedida", 503),
            (ProviderRequestTooLarge, "solicitacao_grande_demais", 413),
        ]:
            with (
                self.subTest(error=error.__name__),
                capture_events() as stream,
                patch(
                    "app.main.responder",
                    new_callable=AsyncMock,
                    side_effect=error("secret-key D:/private Traceback"),
                ),
                self.client() as client,
            ):
                response = client.post("/perguntas", json={"pergunta": "Pergunta"})
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.json()["detail"]["codigo"], code)
                for forbidden in ["secret-key", "D:/private", "Traceback"]:
                    self.assertNotIn(forbidden, response.text)
                    self.assertNotIn(forbidden, stream.getvalue())
                request_id = response.headers.get("X-Request-ID")
                self.assertTrue(request_id)
                terminal = [
                    r
                    for r in events(stream)
                    if r["request_id"] == request_id
                    and r["event"]
                    in {"request_failed", "request_completed", "request_cancelled"}
                ]
                self.assertEqual(len(terminal), 1)
                self.assertEqual(terminal[0]["event"], "request_failed")
                self.assertEqual(terminal[0]["code"], code)
                self.assertEqual(terminal[0]["http_status"], status)
                self.assertEqual(terminal[0]["exception_type"], error.__name__)
                self.assertEqual(
                    terminal[0]["level"],
                    "WARNING" if status == 413 or code == "cota_excedida" else "ERROR",
                )
        with (
            patch.dict(
                os.environ, {"DATABASE_PATH": str(self.path.with_name("ausente.db"))}
            ),
            self.client() as client,
        ):
            self.assertEqual(client.get("/health").status_code, 503)

    def test_configuracao_invalida_sem_fallback(self):
        for config in [
            {"MODEL_PROVIDER": "llamacpp"},
            {"MODEL_BASE_URL": "https://api.openai.com/v1"},
            {"GROQ_API_KEY": ""},
            {"QUESTION_TIMEOUT_SECONDS": "nan"},
        ]:
            with (
                self.subTest(config=config),
                patch.dict(os.environ, config),
                patch("app.main.responder", new_callable=AsyncMock) as respond,
                self.client() as client,
            ):
                self.assertEqual(client.get("/health").status_code, 200)
                response = client.post(
                    "/perguntas", json={"pergunta": "Quantos filmes?"}
                )
                self.assertEqual(response.status_code, 503)
                self.assertEqual(
                    response.json()["detail"]["codigo"], "configuracao_invalida"
                )
                respond.assert_not_called()

    def test_groq_mantem_restricao_de_endereco(self):
        from app.agent import ProviderUnavailable

        with (
            patch(
                "app.main.responder",
                new_callable=AsyncMock,
                side_effect=ProviderUnavailable("offline"),
            ),
            self.client() as client,
        ):
            response = client.post("/perguntas", json={"pergunta": "Quantos filmes?"})
            self.assertEqual(response.json()["detail"]["codigo"], "modelo_indisponivel")
        with (
            patch.dict(os.environ, {"MODEL_BASE_URL": "https://api.openai.com/v1"}),
            self.client() as client,
        ):
            response = client.post("/perguntas", json={"pergunta": "Quantos filmes?"})
            self.assertEqual(
                response.json()["detail"]["codigo"], "configuracao_invalida"
            )

    def test_validation_unknown_route_and_client_id_are_sanitized(self):
        with capture_events() as stream, self.client() as client:
            invalid = client.post(
                "/perguntas?secret=SECRET-QUERY",
                json={"pergunta": "SECRET-QUESTION", "extra": "SECRET-BODY"},
                headers={"X-Request-ID": "SECRET-CLIENT-ID"},
            )
            unknown = client.get("/SECRET-PATH?secret=SECRET-QUERY")
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(unknown.status_code, 404)
        ids = [r.headers.get("X-Request-ID") for r in (invalid, unknown)]
        self.assertTrue(all(ids))
        self.assertEqual(len(set(ids)), 2)
        rows = events(stream)
        terminal = [r for r in rows if r["event"] == "request_failed"]
        self.assertEqual(len(terminal), 2)
        self.assertEqual(terminal[0]["code"], "entrada_invalida")
        self.assertEqual(terminal[0]["level"], "WARNING")
        self.assertEqual(
            [r["route"] for r in rows if r["event"] == "request_started"],
            ["/perguntas", "unknown"],
        )
        self.assertFalse(any(r["event"] == "question_received" for r in rows))
        self.assertNotIn("SECRET", stream.getvalue())

    def test_configuration_lifecycle_and_health_levels(self):
        with (
            capture_events() as stream,
            patch.dict(os.environ, {"GROQ_API_KEY": "", "LOG_LEVEL": "INFO"}),
            self.client() as client,
        ):
            health = client.get("/health")
            response = client.post("/perguntas", json={"pergunta": "SECRET-QUESTION"})
        rows = events(stream)
        self.assertEqual(health.status_code, 200)
        self.assertFalse(
            any(r["request_id"] == health.headers["X-Request-ID"] for r in rows)
        )
        self.assertEqual(
            [r["event"] for r in rows if r["request_id"] is None],
            ["configuration_invalid", "app_started", "app_stopped"],
        )
        terminal = next(r for r in rows if r["event"] == "request_failed")
        self.assertEqual(terminal["code"], "configuracao_invalida")
        self.assertEqual(terminal["stage"], "configuration")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("SECRET", stream.getvalue())

    def test_unexpected_exception_propagates_with_safe_single_finalization(self):
        with (
            capture_events() as stream,
            patch(
                "app.main.responder",
                new_callable=AsyncMock,
                side_effect=RuntimeError("SECRET-ERROR"),
            ),
            self.client() as client,
        ):
            with self.assertRaises(RuntimeError):
                client.post("/perguntas", json={"pergunta": "SECRET-QUESTION"})
        terminal = [
            r
            for r in events(stream)
            if r["event"]
            in {"request_failed", "request_completed", "request_cancelled"}
        ]
        self.assertEqual(len(terminal), 1)
        self.assertEqual(terminal[0]["code"], "erro_inesperado")
        self.assertEqual(terminal[0]["exception_type"], "RuntimeError")
        self.assertTrue(terminal[0]["frames"])
        self.assertNotIn("SECRET", stream.getvalue())


class HTTPConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_requests_and_thread_events_share_their_own_id(self):
        import asyncio
        import httpx
        import logging
        from app.agent import AgentAnswer, QuestionResult
        from app import observability as obs

        prepare_database(self)
        entered = 0
        ready = asyncio.Event()

        async def answer(*args, **kwargs):
            nonlocal entered
            entered += 1
            if entered == 2:
                ready.set()
            await asyncio.wait_for(ready.wait(), 2)
            await asyncio.to_thread(
                obs.log_event, logging.DEBUG, "schema_loaded", duration_ms=1
            )
            return QuestionResult(
                AgentAnswer(status="esclarecimento", resposta="Resposta", avisos=[]),
                [],
                "test",
                {
                    "chamadas": 1,
                    "tokens_entrada": None,
                    "tokens_saida": None,
                    "tentativas_sql": 0,
                },
            )

        with (
            capture_events() as stream,
            patch.dict(
                os.environ, {"LOG_LEVEL": "DEBUG", "DATABASE_PATH": str(self.path)}
            ),
            patch("app.main.create_groq_model", return_value=(object(), AsyncMock())),
            patch("app.main.responder", side_effect=answer),
        ):
            async with (
                main.lifespan(main.app),
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=main.app), base_url="http://test"
                ) as client,
            ):
                responses = await asyncio.gather(
                    *(
                        client.post("/perguntas", json={"pergunta": f"SECRET-{i}"})
                        for i in range(2)
                    )
                )
        ids = [r.headers.get("X-Request-ID") for r in responses]
        self.assertTrue(all(ids))
        self.assertEqual(len(set(ids)), 2)
        for request_id in ids:
            rows = [r for r in events(stream) if r["request_id"] == request_id]
            self.assertEqual(
                [r["event"] for r in rows],
                [
                    "request_started",
                    "question_received",
                    "schema_loaded",
                    "request_completed",
                ],
            )
        self.assertNotIn("SECRET", stream.getvalue())

    async def test_real_cancelled_error_is_logged_once_and_propagated(self):
        import asyncio
        from app.main import RequestLoggingMiddleware
        from app import observability as obs

        async def cancelled(scope, receive, send):
            obs.set_stage("quota_wait")
            raise asyncio.CancelledError()

        with capture_events() as stream:
            with self.assertRaises(asyncio.CancelledError):
                await RequestLoggingMiddleware(cancelled)(
                    {"type": "http", "method": "POST", "path": "/perguntas"},
                    AsyncMock(),
                    AsyncMock(),
                )
        rows = events(stream)
        self.assertEqual(
            [r["event"] for r in rows], ["request_started", "request_cancelled"]
        )
        self.assertEqual(rows[-1]["stage"], "quota_wait")
        self.assertEqual(rows[0]["request_id"], rows[-1]["request_id"])
        self.assertIsNone(obs.current_context())
