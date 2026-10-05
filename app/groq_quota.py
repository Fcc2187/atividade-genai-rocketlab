"""Espaça chamadas ao Groq pelos headers; não repete solicitações rejeitadas."""

import asyncio
from asyncio import CancelledError
import logging
import math
import re
import time

import httpx
from openai import APIConnectionError, APITimeoutError
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models.wrapper import WrapperModel
from app.observability import current_context, error_metadata, log_event, set_stage


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
        set_stage("quota_lock")
        lock_started = time.monotonic()
        async with self._lock:
            log_event(
                logging.DEBUG,
                "quota_lock_wait_finished",
                duration_ms=(time.monotonic() - lock_started) * 1000,
            )
            if time.monotonic() < self._blocked_until:
                log_event(
                    logging.WARNING,
                    "quota_blocked",
                    remaining_ms=max(0, self._blocked_until - time.monotonic()) * 1000,
                    code="cota_excedida",
                )
                raise ModelHTTPError(
                    429,
                    self.model_name,
                    {"message": "Aguarde a reposição da cota do Groq."},
                )
            delay = max(0, self._not_before - time.monotonic())
            if delay:
                set_stage("quota_wait")
                wait_started = time.monotonic()
                log_event(
                    logging.INFO, "quota_wait_started", expected_wait_ms=delay * 1000
                )
                try:
                    await asyncio.sleep(delay)
                except CancelledError:
                    log_event(
                        logging.INFO,
                        "quota_wait_finished",
                        duration_ms=(time.monotonic() - wait_started) * 1000,
                        cancelled=True,
                    )
                    raise
                else:
                    log_event(
                        logging.INFO,
                        "quota_wait_finished",
                        duration_ms=(time.monotonic() - wait_started) * 1000,
                        cancelled=False,
                    )
            # Também reserva uma janela quando uma falha de rede não entrega headers.
            self._not_before = time.monotonic() + 60
            set_stage("model")
            context = current_context()
            call_number = None
            if context is not None:
                context.model_calls += 1
                call_number = context.model_calls
            started = time.monotonic()
            log_event(
                logging.INFO,
                "model_request_started",
                call_number=call_number,
                model=self.model_name,
            )
            try:
                response = await super().request(
                    messages, model_settings, model_request_parameters
                )
            except (Exception, CancelledError) as error:
                provider_status = (
                    error.status_code if isinstance(error, ModelHTTPError) else None
                )
                if isinstance(error, CancelledError):
                    category = "cancelled"
                elif provider_status is not None:
                    category = "http"
                elif isinstance(error, (APITimeoutError, TimeoutError)) or isinstance(
                    error.__cause__, APITimeoutError
                ):
                    category = "timeout"
                elif isinstance(
                    error, (APIConnectionError, httpx.ConnectError)
                ) or isinstance(
                    error.__cause__, (APIConnectionError, httpx.ConnectError)
                ):
                    category = "connection"
                else:
                    category = "unexpected"
                level = (
                    logging.WARNING
                    if category == "cancelled" or provider_status in (413, 429)
                    else logging.ERROR
                )
                log_event(
                    level,
                    "model_request_failed",
                    call_number=call_number,
                    duration_ms=(time.monotonic() - started) * 1000,
                    category=category,
                    provider_status=provider_status,
                    **error_metadata(error),
                )
                raise
            reported = response.usage.has_values()
            log_event(
                logging.INFO,
                "model_request_finished",
                call_number=call_number,
                duration_ms=(time.monotonic() - started) * 1000,
                tokens_entrada=response.usage.input_tokens if reported else None,
                tokens_saida=response.usage.output_tokens if reported else None,
            )
            return response
