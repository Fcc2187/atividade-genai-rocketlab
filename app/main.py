"""API local de perguntas independentes sobre o catálogo fornecido."""

from contextlib import asynccontextmanager
from datetime import date
import math
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.agent import AgentAnswer, InvalidAgentResult, ProviderUnavailable, QuestionTimedOut, create_local_model, responder
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
    return HTTPException(status_code=status, detail={"codigo":code, "mensagem":message})


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv(ROOT / ".env")
    configured_path = Path(os.getenv("DATABASE_PATH", "cinerocket (1).db"))
    app.state.database_path = configured_path if configured_path.is_absolute() else ROOT / configured_path
    app.state.model = None
    app.state.configuration_error = False
    client = None
    try:
        if os.getenv("MODEL_PROVIDER", "llamafile") != "llamafile":
            raise ValueError("Provedor não suportado.")
        timeout = float(os.getenv("QUESTION_TIMEOUT_SECONDS", "180"))
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Prazo inválido.")
        name = os.getenv("MODEL_NAME", "qwen3.5-9b").strip()
        if not name:
            raise ValueError("Nome do modelo ausente.")
        app.state.model, client = create_local_model(os.getenv("MODEL_BASE_URL", "http://127.0.0.1:8081/v1"), name)
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
    return {"status":"ok", "banco":"disponivel"}


@app.post("/perguntas", response_model=QuestionResponse)
async def question(body: QuestionInput):
    if app.state.configuration_error:
        raise failure(503, "configuracao_invalida", "Confira a configuração local do modelo e do prazo.")
    try:
        result = await responder(body.pergunta, app.state.database_path, date.today(), app.state.model,
                                 timeout_seconds=app.state.timeout)
    except DatabaseUnavailable as error:
        raise failure(503, "banco_indisponivel", "Banco indisponível.") from error
    except ProviderUnavailable as error:
        raise failure(503, "modelo_indisponivel", "Inicie o servidor do modelo local.") from error
    except InvalidAgentResult as error:
        raise failure(502, "resposta_invalida", "Resposta inválida do modelo ou limite operacional excedido.") from error
    except QuestionTimedOut as error:
        raise failure(504, "prazo_excedido", "Prazo da pergunta esgotado.") from error
    return QuestionResponse(**result.answer.model_dump(), consultas=result.consultas, modelo=result.modelo, uso=result.uso)
