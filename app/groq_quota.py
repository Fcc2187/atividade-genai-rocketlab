"""Espaça chamadas ao Groq pelos headers; não repete solicitações rejeitadas."""

import asyncio
import math
import re
import time

import httpx
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models.wrapper import WrapperModel


def duration_seconds(value: str) -> float | None:
    parts = re.findall(r"(\d+(?:\.\d+)?)(ms|h|m|s)", value)
    if not parts or "".join(number + unit for number, unit in parts) != value:
        return None
    scales = {"ms": 0.001, "s": 1, "m": 60, "h": 3600}
    seconds = sum(float(number) * scales[unit] for number, unit in parts)
    return seconds if math.isfinite(seconds) else None


class GroqQuotaModel(WrapperModel):
    def __init__(self, wrapped):
        super().__init__(wrapped)
        # ponytail: trava por processo; várias instâncias exigem coordenação pela conta.
        self._lock = asyncio.Lock()
        self._not_before = 0.0
        self._blocked_until = 0.0

    async def record_response(self, response: httpx.Response) -> None:
        now = time.monotonic()
        reset = duration_seconds(response.headers.get("x-ratelimit-reset-tokens", ""))
        self._not_before = now + (reset if reset is not None else 60)
        if response.status_code == 429:
            retry = duration_seconds(response.headers.get("retry-after", "") + "s")
            self._blocked_until = now + (retry if retry is not None else 60)

    async def request(self, messages, model_settings, model_request_parameters):
        async with self._lock:
            if time.monotonic() < self._blocked_until:
                raise ModelHTTPError(
                    429,
                    self.model_name,
                    {"message": "Aguarde a reposição da cota do Groq."},
                )
            delay = max(0, self._not_before - time.monotonic())
            if delay:
                await asyncio.sleep(delay)
            # Também reserva uma janela quando uma falha de rede não entrega headers.
            self._not_before = time.monotonic() + 60
            return await super().request(
                messages, model_settings, model_request_parameters
            )
