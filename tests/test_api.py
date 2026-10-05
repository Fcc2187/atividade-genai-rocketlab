from datetime import date
import os
import unittest
from unittest.mock import AsyncMock, patch
from tests.helpers import prepare_database
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
