"""API local de perguntas independentes sobre o catálogo fornecido."""

from contextlib import asynccontextmanager
from datetime import date
import math
import os
from pathlib import Path

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

ROOT = Path(__file__).resolve().parents[1]


class QuestionInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    pergunta: str = Field(min_length=1, max_length=2000)


class QuestionResponse(AgentAnswer):
    consultas: list[QueryEvidence]
    modelo: str
    uso: dict[str, int | None]


def failure(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status, detail={"codigo": code, "mensagem": message}
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv(ROOT / ".env")
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
    except ValueError:
        app.state.configuration_error = True
    try:
        yield
    finally:
        if client is not None:
            await client.close()


app = FastAPI(title="CineData Analytics", lifespan=lifespan)


@app.get("/health")
def health():
    """Verifica leitura do banco; não verifica nem chama o modelo."""
    try:
        read_schema(app.state.database_path)
    except DatabaseUnavailable as error:
        raise failure(503, "banco_indisponivel", "Banco indisponível.") from error
    return {"status": "ok", "banco": "disponivel"}


@app.post("/perguntas", response_model=QuestionResponse)
async def question(body: QuestionInput):
    if app.state.configuration_error:
        raise failure(
            503,
            "configuracao_invalida",
            "Configure GROQ_API_KEY, o modelo, o endpoint Groq e o prazo.",
        )
    try:
        result = await responder(
            body.pergunta,
            app.state.database_path,
            date.today(),
            app.state.model,
            timeout_seconds=app.state.timeout,
        )
    except DatabaseUnavailable as error:
        raise failure(503, "banco_indisponivel", "Banco indisponível.") from error
    except ProviderUnavailable as error:
        raise failure(
            503,
            "modelo_indisponivel",
            "Groq indisponível; confira conexão e chave de API.",
        ) from error
    except ProviderRateLimited as error:
        raise failure(
            503,
            "cota_excedida",
            "Limite do Groq atingido; aguarde antes de tentar novamente.",
        ) from error
    except ProviderRequestTooLarge as error:
        raise failure(
            413,
            "solicitacao_grande_demais",
            "A solicitação excedeu o tamanho aceito pelo serviço. Peça menos resultados ou use filtros mais específicos.",
        ) from error
    except InvalidAgentResult as error:
        raise failure(
            502,
            "resposta_invalida",
            "Resposta inválida do modelo ou limite operacional excedido.",
        ) from error
    except QuestionTimedOut as error:
        raise failure(504, "prazo_excedido", "Prazo da pergunta esgotado.") from error
    return QuestionResponse(
        **result.answer.model_dump(),
        consultas=result.consultas,
        modelo=result.modelo,
        uso=result.uso,
    )
