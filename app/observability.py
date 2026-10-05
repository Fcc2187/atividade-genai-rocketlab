"""Eventos JSON com campos permitidos e contexto independente por requisição."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
import math
from pathlib import Path
import re
import sys
import traceback


logger = logging.getLogger("cinedata")
logger.propagate = False
# A API configura a saída no lifespan; a CLI de avaliação mantém sua saída atual.
logger.addHandler(logging.NullHandler())

_ERROR_FIELDS = {"exception_type", "frames"}
_EVENT_FIELDS = {
    "log_level_invalid": set(),
    "app_started": {"configured", "model"},
    "app_stopped": set(),
    "configuration_invalid": {"code", "exception_type"},
    "request_started": {"method", "route"},
    "question_received": {"question_chars"},
    "schema_loaded": {"duration_ms"},
    "quota_lock_wait_finished": {"duration_ms"},
    "quota_wait_started": {"expected_wait_ms"},
    "quota_wait_finished": {"duration_ms", "cancelled"},
    "quota_blocked": {"remaining_ms", "code"},
    "model_request_started": {"call_number", "model"},
    "model_request_finished": {
        "call_number",
        "duration_ms",
        "tokens_entrada",
        "tokens_saida",
        "cached_tokens",
        "token_limit",
        "remaining_tokens",
        "reset_tokens_ms",
    },
    "model_request_failed": {
        "call_number",
        "duration_ms",
        "category",
        "provider_status",
    }
    | _ERROR_FIELDS,
    "sql_started": {"attempt"},
    "sql_reused": {"attempt"},
    "sql_finished": {"attempt", "duration_ms", "rows", "truncado"},
    "sql_retry_requested": {"attempt", "code", "duration_ms"},
    "sql_rejected": {"attempt", "category", "duration_ms"},
    "answer_validated": {"response_status", "warnings"},
    "request_completed": {
        "http_status",
        "duration_ms",
        "response_status",
        "chamadas",
        "tokens_entrada",
        "tokens_saida",
        "tentativas_sql",
    },
    "request_failed": {"http_status", "duration_ms", "code", "stage"} | _ERROR_FIELDS,
    "request_cancelled": {"duration_ms", "stage"},
}
_CHOICES = {
    "code": {
        "configuracao_invalida",
        "banco_indisponivel",
        "modelo_indisponivel",
        "cota_excedida",
        "solicitacao_grande_demais",
        "resposta_invalida",
        "prazo_excedido",
        "entrada_invalida",
        "erro_inesperado",
        "erro_http",
        "sql_invalido",
    },
    "stage": {
        "http",
        "configuration",
        "schema",
        "model",
        "quota_lock",
        "quota_wait",
        "sql",
        "answer",
    },
    "category": {
        "http",
        "connection",
        "timeout",
        "cancelled",
        "unexpected",
        "read_only",
        "invalid",
        "deadline",
    },
    "response_status": {"resultado", "esclarecimento", "recusa", "sem_dados"},
    "method": {
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
        "HEAD",
        "TRACE",
        "CONNECT",
    },
    "route": {
        "/health",
        "/perguntas",
        "/docs",
        "/docs/oauth2-redirect",
        "/openapi.json",
        "/redoc",
        "unknown",
    },
}


@dataclass
class RequestContext:
    request_id: str | None
    stage: str = "http"
    failure: dict = field(default_factory=dict)
    result: dict = field(default_factory=dict)
    model_calls: int = 0


_context: ContextVar[RequestContext | None] = ContextVar(
    "cinedata_request", default=None
)


def current_context() -> RequestContext | None:
    return _context.get()


@contextmanager
def request_context(request_id: str | None):
    context = RequestContext(request_id)
    token = _context.set(context)
    try:
        yield context
    finally:
        _context.reset(token)


def set_stage(stage: str) -> None:
    context = current_context()
    if context is not None and stage in _CHOICES["stage"]:
        context.stage = stage


def safe_model_name(value) -> str | None:
    if (
        isinstance(value, str)
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,79}", value)
        and not value.lower().startswith(("sk-", "sk_", "gsk-", "gsk_"))
    ):
        return value
    return None


def _identifier(value, limit=80):
    return (
        value
        if isinstance(value, str)
        and re.fullmatch(r"[A-Za-z0-9_.<>-]{1," + str(limit) + "}", value)
        else None
    )


def error_metadata(error: BaseException) -> dict:
    metadata = {"exception_type": _identifier(type(error).__name__)}
    if logger.isEnabledFor(logging.DEBUG):
        metadata["frames"] = [
            {
                "file": _identifier(Path(frame.filename).name),
                "function": _identifier(frame.name),
                "line": frame.lineno,
            }
            for frame in traceback.extract_tb(error.__traceback__, limit=8)
        ]
    return metadata


def _safe_field(name, value):
    if name in _CHOICES:
        return value if isinstance(value, str) and value in _CHOICES[name] else None
    if name == "model":
        return safe_model_name(value)
    if name == "exception_type":
        return _identifier(value)
    if name in {"configured", "truncado", "cancelled"}:
        return value if type(value) is bool else None
    if name == "frames":
        if not logger.isEnabledFor(logging.DEBUG) or not isinstance(value, list):
            return None
        return [
            {
                "file": _identifier(frame.get("file")),
                "function": _identifier(frame.get("function")),
                "line": _safe_field("line", frame.get("line")),
            }
            for frame in value[:8]
            if isinstance(frame, dict)
        ]
    if type(value) in (int, float) and 0 <= value <= 1e100 and math.isfinite(value):
        return value
    return None


class _JsonFormatter(logging.Formatter):
    def format(self, record):
        # Não usa getMessage/formatException nem serializa objetos do SDK.
        return json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": "cinedata",
                "event": record.event,
                "request_id": record.request_id,
                **record.fields,
            },
            ensure_ascii=True,
            allow_nan=False,
        )


def configure_logging(level: str | None = None) -> None:
    selected = level.upper() if isinstance(level, str) else "INFO"
    valid = selected in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    logger.setLevel(selected if valid else "INFO")
    logger.propagate = False
    handler = next(
        (h for h in logger.handlers if isinstance(h.formatter, _JsonFormatter)), None
    )
    if handler is None:
        handler = logging.StreamHandler()
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)
    handler.stream = sys.stderr
    if not valid:
        log_event(logging.WARNING, "log_level_invalid")


def log_event(level: int, event: str, **fields) -> None:
    if event not in _EVENT_FIELDS or not logger.isEnabledFor(level):
        return
    safe = {
        name: _safe_field(name, value)
        for name, value in fields.items()
        if name in _EVENT_FIELDS[event]
    }
    if not logger.isEnabledFor(logging.DEBUG):
        safe.pop("frames", None)
    context = current_context()
    logger.log(
        level,
        event,
        extra={
            "event": event,
            "request_id": context.request_id if context else None,
            "fields": safe,
        },
    )
