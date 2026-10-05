import asyncio
from datetime import date
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx
from app import agent
from tests.helpers import prepare_database, model_answer
from tests.test_observability import capture_events, events
from app.observability import request_context


class GroqQuotaTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_usage_does_not_create_a_wait(self):
        def handler(request):
            headers = {
                "x-ratelimit-limit-tokens": "8000",
                "x-ratelimit-remaining-tokens": "8000" if not self.sent_at else "1000",
                "x-ratelimit-reset-tokens": "0s" if not self.sent_at else "52.5s",
            }
            response = self.success(request, headers, clarify=True)
            body = response.json()
            if len(self.sent_at) == 1:
                body["usage"]["prompt_tokens"] = 3500
                body["usage"]["total_tokens"] = 3505
            elif len(self.sent_at) == 2:
                del body["usage"]
            return httpx.Response(200, headers=response.headers, json=body)

        model, client = self.make_model(handler)
        try:
            with self.virtual_time():
                for _ in range(3):
                    await agent.responder(
                        "Question", self.path, date(2026, 10, 5), model
                    )
            self.assertEqual(self.sent_at, [100, 100, 100])
        finally:
            await client.close()

    async def test_success_does_not_reserve_previous_input_plus_generation_ceiling(
        self,
    ):
        def handler(request):
            response = self.success(
                request,
                {
                    "x-ratelimit-limit-tokens": "8000",
                    "x-ratelimit-remaining-tokens": "1000",
                    "x-ratelimit-reset-tokens": "52.5s",
                },
            )
            body = response.json()
            body["usage"]["prompt_tokens"] = 3500
            body["usage"]["total_tokens"] = 3505
            return httpx.Response(200, headers=response.headers, json=body)

        model, client = self.make_model(handler)
        try:
            with capture_events() as stream, self.virtual_time():
                await agent.responder("Question", self.path, date(2026, 10, 5), model)
            self.assertEqual(self.sent_at, [100, 100])
            self.assertFalse(
                any(r["event"] == "quota_wait_started" for r in events(stream))
            )
        finally:
            await client.close()

    async def test_known_empty_balance_without_reset_uses_conservative_window(self):
        model, client = self.make_model(
            lambda request: self.success(request, {"x-ratelimit-remaining-tokens": "0"})
        )
        try:
            with self.virtual_time():
                await agent.responder("Question", self.path, date(2026, 10, 5), model)
            self.assertEqual(self.sent_at, [100, 160])
        finally:
            await client.close()

    async def asyncSetUp(self):
        prepare_database(self)
        self.clock = 100.0
        self.sent_at = []

    async def sleep(self, delay):
        self.clock += delay

    def make_model(self, handler):
        transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        with patch(
            "app.agent.httpx", SimpleNamespace(AsyncClient=lambda **kwargs: transport)
        ):
            return agent.create_groq_model(
                "https://api.groq.com/openai/v1", "openai/gpt-oss-120b", "gsk-test"
            )

    def success(self, request, headers, *, clarify=False):
        self.sent_at.append(self.clock)
        body = json.loads(request.content)
        if clarify:
            name, args = "json", model_answer("esclarecimento")[1]
        elif any(message["role"] == "tool" for message in body["messages"]):
            name, args = "json", model_answer()[1]
        else:
            name, args = (
                "consultar_sql",
                {"sql": "SELECT COUNT(*) AS filmes FROM dim_movies", "parametros": {}},
            )
        return httpx.Response(
            200,
            headers=headers,
            json={
                "id": "mock",
                "object": "chat.completion",
                "created": 0,
                "model": "openai/gpt-oss-120b",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": name,
                                    "type": "function",
                                    "function": {
                                        "name": name,
                                        "arguments": json.dumps(args),
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            },
        )

    def virtual_time(self):
        return patch.multiple(
            "app.groq_quota",
            time=SimpleNamespace(monotonic=lambda: self.clock),
            asyncio=SimpleNamespace(Lock=asyncio.Lock, sleep=self.sleep),
        )

    async def test_quota_and_cached_tokens_are_reported_without_headers_or_body(self):
        def handler(request):
            response = self.success(
                request,
                {
                    "x-ratelimit-limit-tokens": "8000",
                    "x-ratelimit-remaining-tokens": "4104",
                    "x-ratelimit-reset-tokens": "28.618s",
                    "authorization": "Bearer SECRET-KEY",
                },
                clarify=True,
            )
            body = response.json()
            body["usage"]["prompt_tokens_details"] = {"cached_tokens": 7}
            return httpx.Response(200, headers=response.headers, json=body)

        model, client = self.make_model(handler)
        try:
            with capture_events() as stream, self.virtual_time():
                await agent.responder(
                    "SECRET-QUESTION", self.path, date(2026, 10, 5), model
                )
            finished = next(
                e for e in events(stream) if e["event"] == "model_request_finished"
            )
            self.assertEqual(finished["token_limit"], 8000)
            self.assertEqual(finished["remaining_tokens"], 4104)
            self.assertEqual(finished["reset_tokens_ms"], 28618)
            self.assertEqual(finished["cached_tokens"], 7)
            self.assertNotIn("SECRET", stream.getvalue())
        finally:
            await client.close()

    async def test_invalid_headers_clear_old_balance_and_do_not_invent_a_wait(self):
        headers = [
            {
                "x-ratelimit-limit-tokens": "8000",
                "x-ratelimit-remaining-tokens": "4104",
                "x-ratelimit-reset-tokens": "30s",
            },
            {
                "x-ratelimit-limit-tokens": "inf",
                "x-ratelimit-remaining-tokens": "-1",
                "x-ratelimit-reset-tokens": "SECRET",
            },
        ]
        model, client = self.make_model(
            lambda request: self.success(request, headers.pop(0))
        )
        try:
            with capture_events() as stream, self.virtual_time():
                await agent.responder("Pergunta", self.path, date(2026, 10, 5), model)
            finished = [
                e for e in events(stream) if e["event"] == "model_request_finished"
            ]
            self.assertIsNone(finished[1]["token_limit"])
            self.assertIsNone(finished[1]["remaining_tokens"])
            self.assertIsNone(finished[1]["reset_tokens_ms"])
            self.assertEqual(self.sent_at, [100, 100])
            self.assertNotIn("SECRET", stream.getvalue())
        finally:
            await client.close()

    async def test_429_expires_at_retry_after_without_extra_reset_wait_or_retry(self):
        def handler(request):
            if not self.sent_at:
                self.sent_at.append(self.clock)
                return httpx.Response(
                    429,
                    headers={
                        "retry-after": "10",
                        "x-ratelimit-reset-tokens": "30s",
                        "x-ratelimit-remaining-tokens": "0",
                    },
                    json={"error": {"message": "limited"}},
                )
            return self.success(request, {}, clarify=True)

        model, client = self.make_model(handler)
        try:
            with capture_events() as stream, self.virtual_time():
                with self.assertRaises(agent.ProviderRateLimited):
                    await agent.responder("First", self.path, date(2026, 10, 5), model)
                self.assertTrue(
                    any(e["event"] == "quota_blocked" for e in events(stream))
                )
                self.clock += 10
                result = await agent.responder(
                    "Next", self.path, date(2026, 10, 5), model
                )
            self.assertEqual(self.sent_at, [100, 110])
            self.assertEqual(result.answer.status, "esclarecimento")
        finally:
            await client.close()

    async def test_sql_success_prevents_duplicate_model_round_and_quota_wait(self):
        requests = []

        def handler(request):
            body = json.loads(request.content)
            requests.append(body)
            response = self.success(request, {"x-ratelimit-reset-tokens": "30s"})
            if len(requests) == 2 and any(
                tool["function"]["name"] == "consultar_sql" for tool in body["tools"]
            ):
                content = response.json()
                content["choices"][0]["message"]["tool_calls"][0]["function"] = {
                    "name": "consultar_sql",
                    "arguments": json.dumps(
                        {
                            "sql": "SELECT COUNT(*) AS filmes FROM dim_movies",
                            "parametros": {},
                        }
                    ),
                }
                return httpx.Response(200, headers=response.headers, json=content)
            return response

        model, client = self.make_model(handler)
        try:
            with capture_events() as stream, self.virtual_time():
                result = await agent.responder(
                    "Pergunta", self.path, date(2026, 10, 5), model
                )
            self.assertEqual(result.uso["chamadas"], 2)
            self.assertEqual(result.uso["tentativas_sql"], 1)
            self.assertEqual(result.uso["tokens_entrada"], 20)
            self.assertEqual(len(result.consultas), 1)
            self.assertEqual(self.sent_at, [100, 100])
            self.assertEqual(
                [tool["function"]["name"] for tool in requests[1]["tools"]], ["json"]
            )
            self.assertTrue(all(body["tool_choice"] == "auto" for body in requests))
            self.assertEqual(
                len(
                    [
                        row
                        for row in events(stream)
                        if row["event"] == "quota_wait_started"
                    ]
                ),
                0,
            )
        finally:
            await client.close()

    async def test_positive_balance_does_not_wait_for_reset_between_calls(
        self,
    ):
        model, client = self.make_model(
            lambda request: self.success(
                request,
                {
                    "x-ratelimit-reset-tokens": "32.257s",
                    "x-ratelimit-limit-tokens": "8000",
                    "x-ratelimit-remaining-tokens": "4104",
                },
            )
        )
        try:
            self.assertTrue(
                callable(getattr(model, "record_response", None)),
                "Modelo deve respeitar os cabeçalhos de cota.",
            )
            with self.virtual_time():
                for question in (
                    "Primeira pergunta",
                    "Segunda pergunta imediatamente depois",
                ):
                    result = await agent.responder(
                        question, self.path, date(2026, 9, 30), model
                    )
                    self.assertEqual(result.consultas[0].linhas, [[2]])
                    self.assertEqual(result.uso["chamadas"], 2)
            self.assertEqual(len(self.sent_at), 4)
            for actual, expected in zip(self.sent_at, [100.0, 100.0, 100.0, 100.0]):
                self.assertAlmostEqual(actual, expected)
        finally:
            await client.close()

    async def test_missing_balance_does_not_invent_wait_and_exhaustion_waits(
        self,
    ):
        headers = [
            {},
            {"x-ratelimit-reset-tokens": "1m2.5s", "x-ratelimit-remaining-tokens": "0"},
            {},
        ]
        model, client = self.make_model(
            lambda request: self.success(
                request, headers.pop(0), clarify=len(self.sent_at) == 2
            )
        )
        try:
            self.assertTrue(callable(getattr(model, "record_response", None)))
            with self.virtual_time():
                await agent.responder(
                    "Uma pergunta", self.path, date(2026, 9, 30), model
                )
                result = await agent.responder(
                    "Outra pergunta", self.path, date(2026, 9, 30), model
                )
                self.assertEqual(result.answer.status, "esclarecimento")
            self.assertEqual(self.sent_at[:3], [100.0, 100.0, 162.5])
        finally:
            await client.close()

    async def test_429_nao_repete_request_e_retry_after_evitaria_envio_prematuro(self):
        def limited(request):
            self.sent_at.append(self.clock)
            return httpx.Response(
                429,
                headers={"retry-after": "10", "x-ratelimit-reset-tokens": "30s"},
                json={
                    "error": {
                        "message": "Quota exceeded",
                        "type": "rate_limit_exceeded",
                        "code": "rate_limit_exceeded",
                    }
                },
            )

        model, client = self.make_model(limited)
        try:
            self.assertTrue(callable(getattr(model, "record_response", None)))
            with self.virtual_time():
                for question in ("Uma pergunta", "Outra pergunta imediatamente depois"):
                    with self.assertRaises(agent.ProviderRateLimited):
                        await agent.responder(
                            question, self.path, date(2026, 9, 30), model
                        )
            self.assertEqual(self.sent_at, [100.0])
        finally:
            await client.close()

    async def test_perguntas_concorrentes_compartilham_a_mesma_janela(self):
        active = 0
        peak = 0

        async def handler(request):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            try:
                await asyncio.sleep(0)
                return self.success(request, {"x-ratelimit-reset-tokens": "30s"})
            finally:
                active -= 1

        model, client = self.make_model(handler)
        try:
            with self.virtual_time():
                results = await asyncio.gather(
                    *(
                        agent.responder(question, self.path, date(2026, 9, 30), model)
                        for question in ("Primeira", "Segunda")
                    )
                )
            self.assertEqual(self.sent_at, [100.0, 100.0, 100.0, 100.0])
            self.assertEqual(peak, 1)
            self.assertTrue(
                all(result.consultas[0].linhas == [[2]] for result in results)
            )
        finally:
            await client.close()

    async def test_413_classificado_como_solicitacao_grande_sem_reenvio(self):
        def too_large(request):
            self.sent_at.append(self.clock)
            return httpx.Response(
                413,
                json={
                    "error": {
                        "message": "Request too large",
                        "code": "rate_limit_exceeded",
                    }
                },
            )

        model, client = self.make_model(too_large)
        try:
            with self.virtual_time(), self.assertRaises(agent.ProviderRequestTooLarge):
                await agent.responder(
                    "Uma pergunta", self.path, date(2026, 9, 30), model
                )
            self.assertEqual(self.sent_at, [100.0])
        finally:
            await client.close()

    async def test_raciocinio_nao_e_reenviado_mas_sql_e_evidencias_sao_preservados(
        self,
    ):
        marker = "raciocinio_intermediario_desnecessario"

        def handler(request):
            response = self.success(request, {"x-ratelimit-reset-tokens": "0s"})
            if len(self.sent_at) == 1:
                body = response.json()
                body["choices"][0]["message"]["reasoning"] = (marker + " ") * 100
                return httpx.Response(200, headers=response.headers, json=body)
            body = json.loads(request.content)
            self.assertNotIn(marker, request.content.decode())
            assistant = next(m for m in body["messages"] if m["role"] == "assistant")
            self.assertNotIn("reasoning", assistant)
            self.assertEqual(
                assistant["tool_calls"][0]["function"]["name"], "consultar_sql"
            )
            self.assertEqual(body["reasoning_effort"], "medium")
            self.assertEqual(body["max_completion_tokens"], 2048)
            return response

        model, client = self.make_model(handler)
        try:
            result = await agent.responder(
                "Quantos filmes?", self.path, date(2026, 9, 30), model
            )
            self.assertEqual(
                result.consultas[0].sql, "SELECT COUNT(*) AS filmes FROM dim_movies"
            )
            self.assertEqual(result.consultas[0].parametros, {})
            self.assertEqual(result.consultas[0].colunas, ["filmes"])
            self.assertEqual(result.consultas[0].linhas, [[2]])
            self.assertFalse(result.consultas[0].truncado)
            self.assertEqual(result.uso["chamadas"], 2)
        finally:
            await client.close()

    async def test_cancelar_durante_espera_libera_trava_sem_enviar_request(self):
        model, client = self.make_model(
            lambda request: self.success(
                request,
                {
                    "x-ratelimit-reset-tokens": "30s",
                    "x-ratelimit-remaining-tokens": "0",
                },
                clarify=True,
            )
        )
        waiting = asyncio.Event()

        async def blocked_sleep(delay):
            waiting.set()
            await asyncio.Event().wait()

        try:
            with self.virtual_time():
                await agent.responder("Primeira", self.path, date(2026, 9, 30), model)
                with patch(
                    "app.groq_quota.asyncio",
                    SimpleNamespace(Lock=asyncio.Lock, sleep=blocked_sleep),
                ):
                    task = asyncio.create_task(
                        agent.responder(
                            "Cancelada", self.path, date(2026, 9, 30), model
                        )
                    )
                    await asyncio.wait_for(waiting.wait(), timeout=1)
                    task.cancel()
                    with self.assertRaises(asyncio.CancelledError):
                        await task
                result = await asyncio.wait_for(
                    agent.responder(
                        "Após cancelar", self.path, date(2026, 9, 30), model
                    ),
                    timeout=1,
                )
            self.assertEqual(self.sent_at, [100.0, 130.0])
            self.assertEqual(result.answer.status, "esclarecimento")
        finally:
            await client.close()

    async def test_model_events_separate_waits_calls_and_usage(self):
        def handler(request):
            response = self.success(
                request,
                {
                    "x-ratelimit-reset-tokens": "30s",
                    "x-ratelimit-remaining-tokens": "0",
                },
            )
            self.clock += 2
            return response

        model, client = self.make_model(handler)
        try:
            with (
                capture_events() as stream,
                request_context("question"),
                self.virtual_time(),
            ):
                result = await agent.responder(
                    "SECRET-QUESTION", self.path, date(2026, 9, 30), model
                )
            rows = events(stream)
            self.assertTrue(all(r["request_id"] == "question" for r in rows))
            self.assertEqual(
                [
                    r["call_number"]
                    for r in rows
                    if r["event"] == "model_request_started"
                ],
                [1, 2],
            )
            finished = [r for r in rows if r["event"] == "model_request_finished"]
            self.assertEqual([r["duration_ms"] for r in finished], [2000, 2000])
            self.assertEqual([r["tokens_entrada"] for r in finished], [10, 10])
            wait = next(r for r in rows if r["event"] == "quota_wait_finished")
            self.assertEqual(wait["duration_ms"], 30000)
            self.assertFalse(wait["cancelled"])
            self.assertEqual(
                next(r for r in rows if r["event"] == "quota_wait_started")[
                    "expected_wait_ms"
                ],
                30000,
            )
            self.assertEqual(result.uso["chamadas"], 2)
            self.assertNotIn("SECRET", stream.getvalue())
            self.assertNotIn("SELECT", stream.getvalue())
        finally:
            await client.close()

    async def test_http_errors_and_local_block_do_not_invent_calls(self):
        for status, error_type in [
            (413, agent.ProviderRequestTooLarge),
            (429, agent.ProviderRateLimited),
        ]:

            def handler(request):
                self.sent_at.append(self.clock)
                return httpx.Response(
                    status,
                    headers={"retry-after": "10"},
                    json={
                        "error": {
                            "message": "SECRET-PROVIDER",
                            "code": "rate_limit_exceeded",
                        }
                    },
                )

            model, client = self.make_model(handler)
            self.sent_at.clear()
            try:
                with (
                    self.subTest(status=status),
                    capture_events() as stream,
                    self.virtual_time(),
                ):
                    with request_context("first"), self.assertRaises(error_type):
                        await agent.responder(
                            "SECRET-QUESTION", self.path, date(2026, 9, 30), model
                        )
                    if status == 429:
                        with request_context("second"), self.assertRaises(error_type):
                            await agent.responder(
                                "SECRET-QUESTION", self.path, date(2026, 9, 30), model
                            )
                rows = events(stream)
                self.assertEqual(len(self.sent_at), 1)
                started = [r for r in rows if r["event"] == "model_request_started"]
                self.assertEqual([r["call_number"] for r in started], [1])
                failed = [r for r in rows if r["event"] == "model_request_failed"]
                self.assertEqual(len(failed), 1)
                self.assertEqual(failed[0]["provider_status"], status)
                self.assertEqual(failed[0]["category"], "http")
                if status == 429:
                    blocked = [r for r in rows if r["event"] == "quota_blocked"]
                    self.assertEqual(
                        [r["request_id"] for r in blocked], ["first", "second"]
                    )
                    self.assertEqual(
                        [r["remaining_ms"] for r in blocked], [10000, 10000]
                    )
                self.assertNotIn("SECRET", stream.getvalue())
            finally:
                await client.close()

    async def test_connection_failure_and_missing_tokens_are_safe(self):
        def offline(request):
            raise httpx.ConnectError("SECRET-CONNECTION", request=request)

        model, client = self.make_model(offline)
        try:
            with (
                capture_events() as stream,
                self.virtual_time(),
                self.assertRaises(agent.ProviderUnavailable),
            ):
                await agent.responder(
                    "SECRET-QUESTION", self.path, date(2026, 9, 30), model
                )
            failed = next(
                r for r in events(stream) if r["event"] == "model_request_failed"
            )
            self.assertEqual(failed["category"], "connection")
            self.assertNotIn("SECRET", stream.getvalue())
        finally:
            await client.close()

        def missing_usage(request):
            response = self.success(request, {}, clarify=True)
            body = response.json()
            del body["usage"]
            return httpx.Response(200, json=body)

        model, client = self.make_model(missing_usage)
        try:
            with capture_events() as stream, self.virtual_time():
                result = await agent.responder(
                    "Pergunta", self.path, date(2026, 9, 30), model
                )
            finished = next(
                r for r in events(stream) if r["event"] == "model_request_finished"
            )
            self.assertIsNone(finished["tokens_entrada"])
            self.assertIsNone(finished["tokens_saida"])
            self.assertIsNone(result.uso["tokens_entrada"])
        finally:
            await client.close()

    async def test_cancelled_quota_wait_is_observed_without_extra_call(self):
        model, client = self.make_model(
            lambda request: self.success(
                request,
                {
                    "x-ratelimit-reset-tokens": "30s",
                    "x-ratelimit-remaining-tokens": "0",
                },
                clarify=True,
            )
        )
        waiting = asyncio.Event()

        async def blocked_sleep(delay):
            waiting.set()
            await asyncio.Event().wait()

        try:
            with capture_events() as stream, self.virtual_time():
                await agent.responder("Primeira", self.path, date(2026, 9, 30), model)
                with patch(
                    "app.groq_quota.asyncio",
                    SimpleNamespace(Lock=asyncio.Lock, sleep=blocked_sleep),
                ):
                    task = asyncio.create_task(
                        agent.responder(
                            "Cancelada", self.path, date(2026, 9, 30), model
                        )
                    )
                    await asyncio.wait_for(waiting.wait(), 1)
                    self.clock += 3
                    task.cancel()
                    with self.assertRaises(asyncio.CancelledError):
                        await task
                result = await asyncio.wait_for(
                    agent.responder(
                        "Após cancelar", self.path, date(2026, 9, 30), model
                    ),
                    1,
                )
            rows = events(stream)
            cancelled = [
                r
                for r in rows
                if r["event"] == "quota_wait_finished" and r["cancelled"]
            ]
            self.assertEqual(len(cancelled), 1)
            self.assertEqual(cancelled[0]["duration_ms"], 3000)
            self.assertEqual(
                len([r for r in rows if r["event"] == "model_request_started"]), 2
            )
            self.assertEqual(result.answer.status, "esclarecimento")
            self.assertEqual(self.sent_at, [100.0, 130.0])
        finally:
            await client.close()

    async def test_api_integration_correlates_real_agent_threads_and_model_calls(self):
        import os
        from app import main

        async def handler(request):
            await asyncio.sleep(0)
            body = json.loads(request.content)
            if any(
                m.get("content") == "SECRET-FAIL"
                for m in body["messages"]
                if m["role"] == "user"
            ):
                return httpx.Response(
                    429,
                    headers={"retry-after": "10"},
                    json={
                        "error": {
                            "message": "SECRET-PROVIDER",
                            "code": "rate_limit_exceeded",
                        }
                    },
                )
            response = self.success(
                request,
                {
                    "x-ratelimit-reset-tokens": "30s",
                    "x-ratelimit-remaining-tokens": "0",
                },
            )
            self.clock += 2
            return response

        model, provider = self.make_model(handler)
        with (
            capture_events() as stream,
            self.virtual_time(),
            patch.dict(
                os.environ,
                {
                    "LOG_LEVEL": "DEBUG",
                    "MODEL_PROVIDER": "groq",
                    "MODEL_NAME": "openai/gpt-oss-120b",
                    "QUESTION_TIMEOUT_SECONDS": "600",
                    "DATABASE_PATH": str(self.path),
                },
            ),
            patch("app.main.create_groq_model", return_value=(model, provider)),
        ):
            async with (
                main.lifespan(main.app),
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=main.app), base_url="http://local"
                ) as client,
            ):
                success = await client.post(
                    "/perguntas", json={"pergunta": "SECRET-SUCCESS"}
                )
                invalid = await client.post(
                    "/perguntas",
                    json={"pergunta": "SECRET-INVALID", "extra": "SECRET-EXTRA"},
                )
                concurrent = await asyncio.gather(
                    *(
                        client.post(
                            "/perguntas", json={"pergunta": f"SECRET-CONCURRENT-{i}"}
                        )
                        for i in range(2)
                    )
                )
                failed = await client.post(
                    "/perguntas", json={"pergunta": "SECRET-FAIL"}
                )
        responses = [success, invalid, *concurrent, failed]
        self.assertEqual([r.status_code for r in responses], [200, 422, 200, 200, 503])
        ids = [r.headers["X-Request-ID"] for r in responses]
        self.assertEqual(len(set(ids)), 5)
        rows = events(stream)
        for response, request_id in zip(responses, ids):
            correlated = [r for r in rows if r["request_id"] == request_id]
            terminal = [
                r
                for r in correlated
                if r["event"]
                in {"request_completed", "request_failed", "request_cancelled"}
            ]
            self.assertEqual(len(terminal), 1)
            self.assertEqual(terminal[0]["http_status"], response.status_code)
            if response.status_code == 200:
                self.assertEqual(
                    [
                        r["call_number"]
                        for r in correlated
                        if r["event"] == "model_request_started"
                    ],
                    [1, 2],
                )
                self.assertEqual(
                    [
                        r["duration_ms"]
                        for r in correlated
                        if r["event"] == "model_request_finished"
                    ],
                    [2000, 2000],
                )
                self.assertEqual(
                    len([r for r in correlated if r["event"] == "sql_finished"]), 1
                )
                self.assertEqual(terminal[0]["tentativas_sql"], 1)
                self.assertTrue(any(r["event"] == "schema_loaded" for r in correlated))
            elif response.status_code == 422:
                self.assertEqual(
                    [r["event"] for r in correlated],
                    ["request_started", "request_failed"],
                )
            else:
                self.assertEqual(terminal[0]["code"], "cota_excedida")
        self.assertTrue(
            any(
                r["event"] == "quota_wait_finished" and r["duration_ms"] == 30000
                for r in rows
            )
        )
        self.assertNotIn("SECRET", stream.getvalue())
        self.assertNotIn("SELECT", stream.getvalue())
        self.assertNotIn("dim_movies", stream.getvalue())
