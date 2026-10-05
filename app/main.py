"""API local de perguntas independentes sobre o catálogo fornecido."""

from contextlib import asynccontextmanager
from datetime import date
import asyncio
import logging
import math
import os
from pathlib import Path
import time
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.agent import (
    AgentAnswer,
    InvalidAgentResult,
    ProviderRateLimited,
    ProviderRequestTooLarge,
    ProviderUnavailable,
    QuestionTimedOut,
    create_groq_model,
    responder,
)
from app.database import DatabaseUnavailable, QueryEvidence, read_schema
from app.observability import (
    configure_logging,
    current_context,
    error_metadata,
    log_event,
    request_context,
    safe_model_name,
    set_stage,
)

ROOT = Path(__file__).resolve().parents[1]


class QuestionInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    pergunta: str = Field(min_length=1, max_length=2000)


class QuestionResponse(AgentAnswer):
    consultas: list[QueryEvidence]
    modelo: str
    uso: dict[str, int | None]


def failure(status: int, code: str, message: str, *, error=None) -> HTTPException:
    context = current_context()
    if context is not None:
        context.failure = {"code": code}
        if error is not None:
            context.failure["exception_type"] = error_metadata(error)["exception_type"]
    return HTTPException(
        status_code=status, detail={"codigo": code, "mensagem": message}
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv(ROOT / ".env")
    configure_logging(os.getenv("LOG_LEVEL", "INFO"))
    configured_path = Path(os.getenv("DATABASE_PATH", "cinerocket (1).db"))
    app.state.database_path = (
        configured_path if configured_path.is_absolute() else ROOT / configured_path
    )
    app.state.model = None
    app.state.configuration_error = False
    client = None
    try:
        if os.getenv("MODEL_PROVIDER", "groq") != "groq":
            raise ValueError("Provedor não suportado.")
        timeout = float(os.getenv("QUESTION_TIMEOUT_SECONDS", "600"))
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Prazo inválido.")
        name = os.getenv("MODEL_NAME", "openai/gpt-oss-120b").strip()
        if not name:
            raise ValueError("Nome do modelo ausente.")
        app.state.model, client = create_groq_model(
            os.getenv("MODEL_BASE_URL", "https://api.groq.com/openai/v1"),
            name,
            os.getenv("GROQ_API_KEY", ""),
        )
        app.state.timeout = timeout
    except ValueError as error:
        app.state.configuration_error = True
        log_event(
            logging.ERROR,
            "configuration_invalid",
            code="configuracao_invalida",
            exception_type=type(error).__name__,
        )
    log_event(
        logging.INFO,
        "app_started",
        configured=not app.state.configuration_error,
        model=safe_model_name(app.state.model.model_name)
        if app.state.model is not None and hasattr(app.state.model, "model_name")
        else None,
    )
    try:
        yield
    finally:
        try:
            if client is not None:
                await client.close()
        finally:
            log_event(logging.INFO, "app_stopped")


class RequestLoggingMiddleware:
    """Observe o ciclo HTTP completo sem ler o corpo nem reconstruir a resposta."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        known_routes = {
            "/health",
            "/perguntas",
            "/docs",
            "/docs/oauth2-redirect",
            "/openapi.json",
            "/redoc",
        }
        route = scope.get("path")
        route = route if route in known_routes else "unknown"
        usual_level = logging.DEBUG if route == "/health" else logging.INFO
        started = time.monotonic()
        status = 500
        with request_context(uuid4().hex) as context:
            log_event(
                usual_level, "request_started", method=scope.get("method"), route=route
            )

            async def correlated_send(message):
                nonlocal status
                if message["type"] == "http.response.start":
                    status = message["status"]
                    message = {
                        **message,
                        "headers": [
                            *(
                                h
                                for h in message.get("headers", [])
                                if h[0].lower() != b"x-request-id"
                            ),
                            (b"x-request-id", context.request_id.encode("ascii")),
                        ],
                    }
                await send(message)

            try:
                await self.app(scope, receive, correlated_send)
            except asyncio.CancelledError:
                log_event(
                    logging.WARNING,
                    "request_cancelled",
                    stage=context.stage,
                    duration_ms=(time.monotonic() - started) * 1000,
                )
                raise
            except Exception as error:
                log_event(
                    logging.ERROR,
                    "request_failed",
                    http_status=500,
                    code="erro_inesperado",
                    stage=context.stage,
                    duration_ms=(time.monotonic() - started) * 1000,
                    **error_metadata(error),
                )
                raise
            else:
                duration = (time.monotonic() - started) * 1000
                if status >= 400:
                    fields = context.failure or {
                        "code": "entrada_invalida" if status == 422 else "erro_http"
                    }
                    level = (
                        logging.WARNING
                        if status < 500 or fields["code"] == "cota_excedida"
                        else logging.ERROR
                    )
                    log_event(
                        level,
                        "request_failed",
                        http_status=status,
                        duration_ms=duration,
                        stage=context.stage,
                        **fields,
                    )
                else:
                    log_event(
                        usual_level,
                        "request_completed",
                        http_status=status,
                        duration_ms=duration,
                        **context.result,
                    )


app = FastAPI(title="CineData Analytics", lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)


@app.get("/health")
def health():
    """Verifica leitura do banco; não verifica nem chama o modelo."""
    try:
        set_stage("schema")
        read_schema(app.state.database_path)
    except DatabaseUnavailable as error:
        raise failure(
            503, "banco_indisponivel", "Banco indisponível.", error=error
        ) from error
    return {"status": "ok", "banco": "disponivel"}


@app.post("/perguntas", response_model=QuestionResponse)
async def question(body: QuestionInput):
    log_event(logging.INFO, "question_received", question_chars=len(body.pergunta))
    if app.state.configuration_error:
        set_stage("configuration")
        raise failure(
            503,
            "configuracao_invalida",
            "Configure GROQ_API_KEY, o modelo, o endpoint Groq e o prazo.",
        )
    try:
        set_stage("model")
        result = await responder(
            body.pergunta,
            app.state.database_path,
            date.today(),
            app.state.model,
            timeout_seconds=app.state.timeout,
        )
    except DatabaseUnavailable as error:
        raise failure(
            503, "banco_indisponivel", "Banco indisponível.", error=error
        ) from error
    except ProviderUnavailable as error:
        raise failure(
            503,
            "modelo_indisponivel",
            "Groq indisponível; confira conexão e chave de API.",
            error=error,
        ) from error
    except ProviderRateLimited as error:
        raise failure(
            503,
            "cota_excedida",
            "Limite do Groq atingido; aguarde antes de tentar novamente.",
            error=error,
        ) from error
    except ProviderRequestTooLarge as error:
        raise failure(
            413,
            "solicitacao_grande_demais",
            "A solicitação excedeu o tamanho aceito pelo serviço. Peça menos resultados ou use filtros mais específicos.",
            error=error,
        ) from error
    except InvalidAgentResult as error:
        raise failure(
            502,
            "resposta_invalida",
            "Resposta inválida do modelo ou limite operacional excedido.",
            error=error,
        ) from error
    except QuestionTimedOut as error:
        raise failure(
            504, "prazo_excedido", "Prazo da pergunta esgotado.", error=error
        ) from error
    context = current_context()
    if context is not None:
        context.result = {"response_status": result.answer.status, **result.uso}
    return QuestionResponse(
        **result.answer.model_dump(),
        consultas=result.consultas,
        modelo=result.modelo,
        uso=result.uso,
    )
