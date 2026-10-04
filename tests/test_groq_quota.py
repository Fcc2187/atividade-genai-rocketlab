import asyncio
from datetime import date
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx
from app import agent
from tests.helpers import prepare_database, model_answer


class GroqQuotaTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        prepare_database(self)
        self.clock = 100.0
        self.sent_at = []

    async def sleep(self, delay):
        self.clock += delay

    def make_model(self, handler):
        transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        with patch('app.agent.httpx', SimpleNamespace(AsyncClient=lambda **kwargs: transport)):
            return agent.create_groq_model('https://api.groq.com/openai/v1', 'openai/gpt-oss-120b', 'gsk-test')

    def success(self, request, headers, *, clarify=False):
        self.sent_at.append(self.clock)
        body = json.loads(request.content)
        if clarify:
            name, args = 'json', model_answer('esclarecimento')[1]
        elif any(message['role'] == 'tool' for message in body['messages']):
            name, args = 'json', model_answer()[1]
        else:
            name, args = 'consultar_sql', {'sql': 'SELECT COUNT(*) AS filmes FROM dim_movies', 'parametros': {}}
        return httpx.Response(200, headers=headers, json={
            'id': 'mock', 'object': 'chat.completion', 'created': 0, 'model': 'openai/gpt-oss-120b',
            'choices': [{'index': 0, 'message': {'role': 'assistant', 'tool_calls': [
                {'id': name, 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(args)}}]},
                'finish_reason': 'tool_calls'}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}})

    def virtual_time(self):
        return patch.multiple('app.groq_quota', time=SimpleNamespace(monotonic=lambda: self.clock),
                              asyncio=SimpleNamespace(Lock=asyncio.Lock, sleep=self.sleep))

    async def test_respeita_reset_dentro_da_pergunta_e_entre_perguntas_sem_reenvio(self):
        model, client = self.make_model(lambda request: self.success(request, {'x-ratelimit-reset-tokens': '32.257s'}))
        try:
            self.assertTrue(callable(getattr(model, 'record_response', None)), 'Modelo deve respeitar os cabeçalhos de cota.')
            with self.virtual_time():
                for question in ('Primeira pergunta', 'Segunda pergunta imediatamente depois'):
                    result = await agent.responder(question, self.path, date(2026, 9, 30), model)
                    self.assertEqual(result.consultas[0].linhas, [[2]])
                    self.assertEqual(result.uso['chamadas'], 2)
            self.assertEqual(len(self.sent_at), 4)
            for actual, expected in zip(self.sent_at, [100.0, 132.257, 164.514, 196.771]):
                self.assertAlmostEqual(actual, expected)
        finally:
            await client.close()

    async def test_sem_header_usa_espera_conservadora_e_header_composto_e_respeitado(self):
        headers = [{}, {'x-ratelimit-reset-tokens': '1m2.5s'}, {}]
        model, client = self.make_model(lambda request: self.success(request, headers.pop(0), clarify=len(self.sent_at) == 2))
        try:
            self.assertTrue(callable(getattr(model, 'record_response', None)))
            with self.virtual_time():
                await agent.responder('Uma pergunta', self.path, date(2026, 9, 30), model)
                result = await agent.responder('Outra pergunta', self.path, date(2026, 9, 30), model)
                self.assertEqual(result.answer.status, 'esclarecimento')
            self.assertEqual(self.sent_at[:3], [100.0, 160.0, 222.5])
        finally:
            await client.close()

    async def test_429_nao_repete_request_e_retry_after_evitaria_envio_prematuro(self):
        def limited(request):
            self.sent_at.append(self.clock)
            return httpx.Response(429, headers={'retry-after': '10', 'x-ratelimit-reset-tokens': '30s'},
                                  json={'error': {'message': 'Quota exceeded', 'type': 'rate_limit_exceeded', 'code': 'rate_limit_exceeded'}})
        model, client = self.make_model(limited)
        try:
            self.assertTrue(callable(getattr(model, 'record_response', None)))
            with self.virtual_time():
                for question in ('Uma pergunta', 'Outra pergunta imediatamente depois'):
                    with self.assertRaises(agent.ProviderRateLimited):
                        await agent.responder(question, self.path, date(2026, 9, 30), model)
            self.assertEqual(self.sent_at, [100.0])
        finally:
            await client.close()

    async def test_perguntas_concorrentes_compartilham_a_mesma_janela(self):
        async def handler(request):
            await asyncio.sleep(0)
            return self.success(request, {'x-ratelimit-reset-tokens': '30s'})
        model, client = self.make_model(handler)
        try:
            with self.virtual_time():
                results = await asyncio.gather(*(agent.responder(question, self.path, date(2026, 9, 30), model)
                                                for question in ('Primeira', 'Segunda')))
            self.assertEqual(self.sent_at, [100.0, 130.0, 160.0, 190.0])
            self.assertTrue(all(result.consultas[0].linhas == [[2]] for result in results))
        finally:
            await client.close()

    async def test_cancelar_durante_espera_libera_trava_sem_enviar_request(self):
        model, client = self.make_model(lambda request: self.success(request, {'x-ratelimit-reset-tokens': '30s'}, clarify=True))
        waiting = asyncio.Event()
        async def blocked_sleep(delay):
            waiting.set()
            await asyncio.Event().wait()
        try:
            with self.virtual_time():
                await agent.responder('Primeira', self.path, date(2026, 9, 30), model)
                with patch('app.groq_quota.asyncio', SimpleNamespace(Lock=asyncio.Lock, sleep=blocked_sleep)):
                    task = asyncio.create_task(agent.responder('Cancelada', self.path, date(2026, 9, 30), model))
                    await asyncio.wait_for(waiting.wait(), timeout=1)
                    task.cancel()
                    with self.assertRaises(asyncio.CancelledError):
                        await task
                result = await asyncio.wait_for(agent.responder('Após cancelar', self.path, date(2026, 9, 30), model), timeout=1)
            self.assertEqual(self.sent_at, [100.0, 130.0])
            self.assertEqual(result.answer.status, 'esclarecimento')
        finally:
            await client.close()
