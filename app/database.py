"""Acesso limitado ao SQLite estático recebido, sem operações de escrita."""

from contextlib import closing
from dataclasses import dataclass
import json
import math
from pathlib import Path
import sqlite3
import time
from threading import Event

SQLValue = str | int | float | None
SQLParams = dict[str, SQLValue]

TABLES = frozenset({
    "dim_movies", "fact_movies_performance", "dim_people", "dim_genres",
    "dim_companies", "dim_reviews", "movie_reviews", "bridge_movie_person",
    "bridge_movie_genre", "bridge_movie_company",
})
FUNCTIONS = frozenset({
    "count", "sum", "total", "avg", "min", "max", "abs", "round",
    "coalesce", "ifnull", "nullif", "lower", "upper", "trim", "ltrim",
    "rtrim", "length", "substr", "substring", "instr", "replace", "like",
    "date", "datetime", "strftime", "julianday", "unixepoch", "iif",
    "row_number", "rank", "dense_rank", "lag", "lead",
})


class DatabaseUnavailable(Exception):
    """Arquivo ausente, inválido ou com estado de escrita pendente."""


class QueryRejected(Exception):
    """Operação fora das permissões de leitura."""


class QueryTimedOut(Exception):
    """Prazo da consulta esgotado."""


class QueryInvalid(Exception):
    """Consulta, parâmetros ou formato de resultado inválidos."""


@dataclass
class QueryEvidence:
    sql: str
    parametros: SQLParams
    colunas: list[str]
    linhas: list[list[SQLValue]]
    truncado: bool


def _connect(path: Path) -> sqlite3.Connection:
    try:
        resolved = Path(path).resolve(strict=True)
        if not resolved.is_file():
            raise DatabaseUnavailable("Banco indisponível.")
        if any(Path(str(resolved) + suffix).exists() for suffix in ("-wal", "-journal")):
            raise DatabaseUnavailable("Banco com escrita pendente; use uma cópia estática consistente.")
        # immutable só é adequado à base estática deste projeto; não usar em uma base em atualização.
        connection = sqlite3.connect(resolved.as_uri() + "?mode=ro&immutable=1", uri=True)
        try:
            connection.execute("SELECT name FROM sqlite_master LIMIT 1").fetchall()
        except sqlite3.Error:
            connection.close()
            raise
        return connection
    except (OSError, RuntimeError, sqlite3.Error) as error:
        raise DatabaseUnavailable("Banco indisponível ou inválido.") from error


def _tables(connection: sqlite3.Connection) -> dict[str, set[str]]:
    return {
        name: {column[1].casefold() for column in connection.execute(f'PRAGMA table_info("{name}")')}
        for name in TABLES
        if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    }


def read_schema(path: Path) -> str:
    """DDL com colunas/chaves das tabelas de negócio, obtido por código de confiança."""
    with closing(_connect(path)) as connection:
        statements = connection.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name")
        return "\n".join(sql for name, sql in statements if name in TABLES)


def execute_readonly(
    path: Path, sql: str, parametros: SQLParams, *,
    timeout_seconds: float = 20.0, deadline: float | None = None, cancel: Event | None = None,
) -> QueryEvidence:
    """Executa uma leitura; limites contam erros e não dependem das instruções do modelo."""
    if not isinstance(sql, str) or not sql.strip() or len(sql) > 10000:
        raise QueryInvalid("SQL vazio ou acima do limite.")
    if not isinstance(parametros, dict) or len(parametros) > 50:
        raise QueryInvalid("Parâmetros inválidos ou acima do limite.")
    for key, value in parametros.items():
        if not isinstance(key, str) or not key or len(key) > 64:
            raise QueryInvalid("Nome de parâmetro inválido.")
        if type(value) not in (str, int, float, type(None)):
            raise QueryInvalid("Parâmetros devem ser escalares JSON.")
        if isinstance(value, float) and not math.isfinite(value):
            raise QueryInvalid("Números devem ser finitos.")
        if isinstance(value, int) and not -(2**63) <= value < 2**63:
            raise QueryInvalid("Inteiro fora do intervalo do SQLite.")
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise QueryInvalid("Prazo SQL inválido.")
    if deadline is not None and not math.isfinite(deadline):
        raise QueryInvalid("Prazo da pergunta inválido.")
    expires = min(time.monotonic() + timeout_seconds, deadline if deadline is not None else math.inf)
    def interrupted():
        return time.monotonic() >= expires or cancel is not None and cancel.is_set()

    if interrupted():
        raise QueryTimedOut("Prazo da consulta esgotado.")
    parameters = dict(parametros)
    denied = False

    with closing(_connect(path)) as connection:
        columns = _tables(connection)

        def authorize(action, first, second, database, source):
            nonlocal denied
            allowed = action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE)
            if action == sqlite3.SQLITE_READ:
                allowed = (
                    first in columns and (
                        database == "main" and (not second or second.casefold() in columns[first])
                        # O SQLite omite o banco/coluna no acesso otimizado de COUNT(*).
                        or database is None and not second
                    )
                )
            elif action == sqlite3.SQLITE_FUNCTION:
                allowed = (second or "").casefold() in FUNCTIONS
            if not allowed:
                denied = True
            return sqlite3.SQLITE_OK if allowed else sqlite3.SQLITE_DENY

        connection.set_authorizer(authorize)
        connection.set_progress_handler(lambda: int(interrupted()), 1000)
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 1_000_000)
        connection.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 10000)
        connection.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 64)
        try:
            if interrupted():
                raise QueryTimedOut("Prazo da consulta esgotado.")
            cursor = connection.execute(sql, parameters)
            if cursor.description is None:
                raise QueryRejected("Somente consultas de leitura são permitidas.")
            names = [column[0] for column in cursor.description]
            rows: list[list[SQLValue]] = []
            truncated = False
            for index, row in enumerate(cursor):
                if interrupted():
                    raise QueryTimedOut("Prazo da consulta esgotado.")
                if index == 100:
                    truncated = True
                    break
                values: list[SQLValue] = []
                for value in row:
                    if isinstance(value, bytes) or (isinstance(value, float) and not math.isfinite(value)):
                        raise QueryInvalid("Resultado não representável como JSON.")
                    if isinstance(value, str) and len(value) > 2000:
                        value = value[:1999] + "…"
                        truncated = True
                    values.append(value)
                payload = {"colunas": names, "linhas": rows + [values], "truncado": truncated}
                if len(json.dumps(payload, ensure_ascii=False, allow_nan=False)) > 12000:
                    if not rows:
                        raise QueryInvalid("Resultado muito largo; selecione menos colunas ou texto.")
                    truncated = True
                    break
                rows.append(values)
            return QueryEvidence(sql, parameters, names, rows, truncated)
        except sqlite3.Error as error:
            if denied:
                raise QueryRejected("Operação SQL não autorizada.") from error
            if getattr(error, "sqlite_errorcode", None) == sqlite3.SQLITE_INTERRUPT:
                raise QueryTimedOut("Prazo da consulta esgotado.") from error
            if isinstance(error, sqlite3.ProgrammingError) and "one statement" in str(error).lower():
                raise QueryRejected("Somente uma instrução SQL é permitida.") from error
            raise QueryInvalid("SQL ou parâmetros inválidos.") from error
