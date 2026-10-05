from datetime import date
import json
import unittest
from tests.helpers import prepare_database, model_answer
from app import agent


class GroqAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        prepare_database(self)
        self.agent = agent

    async def test_adapter_valida_ferramenta_e_texto_json_sem_forcar_groq(self):
        import httpx
        from openai import AsyncOpenAI
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        probe, real_client = self.agent.create_groq_model(
            "https://api.groq.com/openai/v1", "openai/gpt-oss-120b", "gsk-test"
        )
        profile = probe.profile
        await real_client.close()
        requests = []
        invalid = False
        raw = False
        missing_warnings = False

        def transport(request):
            self.assertEqual(
                str(request.url), "https://api.groq.com/openai/v1/chat/completions"
            )
            self.assertEqual(request.headers["authorization"], "Bearer gsk-test")
            body = json.loads(request.content)
            if "response_format" in body:
                return httpx.Response(
                    400,
                    json={
                        "error": {
                            "message": "json mode cannot be combined with tool/function calling"
                        }
                    },
                )
            self.assertNotIn("chat_template_kwargs", body)
            self.assertEqual(body["reasoning_effort"], "medium")
            self.assertEqual(body["max_completion_tokens"], 2048)
            requests.append(body)
            if len(requests) == 1:
                output_tool = next(
                    t for t in body["tools"] if t["function"]["name"] == "json"
                )
                self.assertIn(
                    "avisos", output_tool["function"]["parameters"]["required"]
                )
                self.assertEqual(body["messages"][0]["role"], "system")
                policies = "\n".join(
                    str(m.get("content", ""))
                    for m in body["messages"]
                    if m["role"] in ("system", "developer")
                )
                self.assertIn(
                    "lucro acumulado filtra receita e orçamento não nulos", policies
                )
                self.assertIn("Toda AVG calculada", policies)
                sql_tool = next(
                    t for t in body["tools"] if t["function"]["name"] == "consultar_sql"
                )
                self.assertEqual(
                    sql_tool["function"]["parameters"]["required"],
                    ["sql", "parametros"],
                )
                self.assertIn("receita_usd IS NOT NULL", policies)
            if len(requests) == 1:
                message = {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "sql",
                            "type": "function",
                            "function": {
                                "name": "consultar_sql",
                                "arguments": json.dumps(
                                    {
                                        "sql": "SELECT COUNT(*) AS filmes FROM dim_movies",
                                        "parametros": {},
                                    }
                                ),
                            },
                        }
                    ],
                }
                reason = "tool_calls"
            else:
                self.assertEqual(
                    [t["function"]["name"] for t in body["tools"]], ["json"]
                )
                if body["tool_choice"] != "auto":
                    return httpx.Response(
                        400,
                        json={
                            "error": {
                                "message": "Tool choice is required, but model did not call a tool",
                                "code": "tool_use_failed",
                            }
                        },
                    )
                answer = model_answer()[1]
                if missing_warnings:
                    del answer["avisos"]
                message = {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "answer",
                            "type": "function",
                            "function": {
                                "name": "json",
                                "arguments": "{}" if invalid else json.dumps(answer),
                            },
                        }
                    ],
                }
                reason = "tool_calls"
                if raw:
                    message = {
                        "role": "assistant",
                        "content": "{}" if invalid else json.dumps(answer),
                    }
                    reason = "stop"
            return httpx.Response(
                200,
                json={
                    "id": "mock",
                    "object": "chat.completion",
                    "created": 0,
                    "model": "openai/gpt-oss-120b",
                    "choices": [
                        {"index": 0, "message": message, "finish_reason": reason}
                    ],
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 5,
                        "total_tokens": 15,
                    },
                },
            )

        client = AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key="gsk-test",
            max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(transport)),
        )
        try:
            model = OpenAIChatModel(
                "openai/gpt-oss-120b",
                provider=OpenAIProvider(openai_client=client),
                profile=profile,
            )
            result = await self.agent.responder(
                "Quantos filmes?", self.path, date(2026, 9, 30), model
            )
            self.assertEqual(result.answer.status, "resultado")
            self.assertEqual(len(requests), 2)
            self.assertTrue(all(r["tool_choice"] == "auto" for r in requests))
            self.assertTrue(all("response_format" not in body for body in requests))
            requests.clear()
            raw = True
            result = await self.agent.responder(
                "Quantos filmes?", self.path, date(2026, 9, 30), model
            )
            self.assertEqual(result.answer.status, "resultado")
            self.assertEqual(len(requests), 2)
            requests.clear()
            missing_warnings = True
            for raw in (False, True):
                with self.subTest(raw=raw):
                    with self.assertRaises(self.agent.InvalidAgentResult):
                        await self.agent.responder(
                            "Quantos filmes?", self.path, date(2026, 9, 30), model
                        )
                    self.assertEqual(len(requests), 2)
                    requests.clear()
            missing_warnings = False
            invalid = True
            with self.assertRaises(self.agent.InvalidAgentResult):
                await self.agent.responder(
                    "Quantos filmes?", self.path, date(2026, 9, 30), model
                )
            self.assertEqual(len(requests), 2)  # Saída inválida não gera retry oculto.
        finally:
            await client.close()
