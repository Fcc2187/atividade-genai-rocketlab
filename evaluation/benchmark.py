"""Medições reais, sequenciais e sem retries; relatórios locais em runtime/."""

import argparse
import asyncio
from contextlib import nullcontext
from dataclasses import asdict
from datetime import date
import json
import hashlib
import logging
import math
import os
import re
from pathlib import Path
import statistics
import time
from unittest.mock import patch

from dotenv import load_dotenv

from evaluation.run import ROOT, load_cases
from evaluation.grading import grade


BENCHMARK_IDS = (
    "04_populares",
    "06_nota_ano",
    "01_receita_brl",
    "11_produtora_lucro",
    "10_filmes_genero",
    "08_diretor_nota",
    "09_par_ator_diretor",
    "20_anos_parciais",
    "13_mais_avaliacoes",
    "15_sem_dados",
)


def select_benchmark_cases(cases):
    by_id = {c["id"]: c for c in cases}
    return [by_id[key] for key in BENCHMARK_IDS]


def rate_limit_dimension(message):
    """Exporta só a dimensão conhecida; nunca o texto ou identificador da conta."""
    if not isinstance(message, str):
        return None
    dimensions = set(re.findall(r"\((TPM|TPD|RPM|RPD|ITPM|OTPM)\)", message))
    return next(iter(dimensions)) if len(dimensions) == 1 else None


def summarize(rows):
    successful = [r for r in rows if r["veredito"] != "erro"]
    result = {
        "successful_cases": len(successful),
        "errors": len(rows) - len(successful),
    }
    for field in (
        "total_ms",
        "quota_wait_ms",
        "model_ms",
        "sql_ms",
        "tokens_entrada",
        "tokens_saida",
        "cached_tokens",
        "calls",
        "sql_executions",
    ):
        values = sorted(r[field] for r in successful if r.get(field) is not None)
        result[field] = (
            {
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "p95": values[math.ceil(len(values) * 0.95) - 1],
            }
            if values
            else None
        )
    result["correct_cases"] = sum(r["veredito"] == "correto" for r in rows)
    return result


class Metrics(logging.Handler):
    def __init__(self):
        super().__init__()
        self.rows = []

    def emit(self, record):
        self.rows.append({"event": record.event, **record.fields})


async def benchmark(cases, database, output, *, interval=30, stable_tools=False):
    from app import agent
    from app.database import execute_readonly
    from app.observability import configure_logging, logger

    configure_logging("INFO")
    capture = Metrics()
    logger.addHandler(capture)
    model, client = agent.create_groq_model(
        os.getenv("MODEL_BASE_URL", "https://api.groq.com/openai/v1"),
        os.getenv("MODEL_NAME", "openai/gpt-oss-120b"),
        os.getenv("GROQ_API_KEY", ""),
    )
    cached = []
    provider_diagnostics = []

    async def record_cache(response):
        # Only numeric cache usage leaves this callback; never store headers/body.
        await response.aread()
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        if response.status_code == 200:
            value = (payload.get("usage") or {}).get("prompt_tokens_details") or {}
            # O SDK também interpreta ausência de cache details como zero.
            count = value.get("cached_tokens", 0)
            cached.append(count if type(count) is int and count >= 0 else None)
        else:
            body = payload.get("error") or {}
            if not isinstance(body, dict):
                body = {}
            code = body.get("code")
            provider_diagnostics.append(
                {
                    "status": response.status_code,
                    "code": code
                    if code
                    in (
                        "tool_use_failed",
                        "rate_limit_exceeded",
                        "invalid_request_error",
                    )
                    else None,
                    "attempted_sql": "consultar_sql"
                    in str(body.get("failed_generation", "")),
                    "rate_limit_dimension": rate_limit_dimension(body.get("message")),
                    "requested_tokens": int(match.group(1))
                    if (
                        match := re.search(
                            r"Requested[: ]+([0-9]+)", str(body.get("message", ""))
                        )
                    )
                    else None,
                }
            )

    client._client.event_hooks["response"].append(record_cache)
    report = {
        "tools": "stable" if stable_tools else "dynamic",
        "interval_seconds": interval,
        "model": model.model_name,
        "cases": [],
        "code_sha256": {
            name: hashlib.sha256((ROOT / "app" / name).read_bytes()).hexdigest()
            for name in ("agent.py", "groq_quota.py", "prompts.py")
        },
    }
    original_tool = agent.Agent.tool

    def stable_tool(self, *args, **kwargs):
        kwargs.pop("prepare", None)
        return original_tool(self, *args, **kwargs)

    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with (
            patch.object(agent.Agent, "tool", stable_tool)
            if stable_tools
            else nullcontext()
        ):
            for index, case in enumerate(cases):
                if index and interval:
                    await asyncio.sleep(interval)
                capture.rows.clear()
                cached.clear()
                provider_diagnostics.clear()
                expected = [
                    execute_readonly(database, r["sql"], r["parametros"])
                    for r in case["referencias"]
                ]
                row = {"id": case["id"]}
                started = time.monotonic()
                print(f"Starting {case['id']}", flush=True)
                fatal = False
                try:
                    result = await agent.responder(
                        case["pergunta"],
                        database,
                        date.fromisoformat(case["data_referencia"]),
                        model,
                    )
                    obtained = asdict(result)
                    obtained["answer"] = result.answer.model_dump()
                    status_ok, rows_ok = grade(case, expected, obtained)
                    row.update(
                        veredito="correto" if status_ok and rows_ok else "incorreto",
                        status_ok=status_ok,
                        rows_ok=rows_ok,
                        obtained=obtained,
                    )
                except (
                    agent.ProviderRateLimited,
                    agent.ProviderUnavailable,
                    agent.ProviderRequestTooLarge,
                    agent.QuestionTimedOut,
                    agent.InvalidAgentResult,
                ) as error:
                    row.update(veredito="erro", error=type(error).__name__)
                    fatal = isinstance(
                        error,
                        (
                            agent.ProviderRateLimited,
                            agent.ProviderUnavailable,
                            agent.QuestionTimedOut,
                        ),
                    )
                row["total_ms"] = (time.monotonic() - started) * 1000
                finished = [
                    e for e in capture.rows if e["event"] == "model_request_finished"
                ]
                row["model_calls"] = [
                    e
                    for e in capture.rows
                    if e["event"] in ("model_request_finished", "model_request_failed")
                ]
                row["calls"] = sum(
                    e["event"] == "model_request_started" for e in capture.rows
                )
                row["sql_executions"] = sum(
                    e["event"] == "sql_started" for e in capture.rows
                )
                row["sql_successes"] = sum(
                    e["event"] == "sql_finished" for e in capture.rows
                )
                row["quota_wait_ms"] = sum(
                    e["duration_ms"]
                    for e in capture.rows
                    if e["event"] == "quota_wait_finished"
                )
                row["sql_ms"] = sum(
                    e["duration_ms"]
                    for e in capture.rows
                    if e["event"]
                    in ("sql_finished", "sql_retry_requested", "sql_rejected")
                )
                row["model_ms"] = sum(e["duration_ms"] for e in row["model_calls"])
                row["usage_complete"] = len(finished) == row["calls"]
                for field in ("tokens_entrada", "tokens_saida"):
                    row[field] = (
                        sum(e[field] for e in finished)
                        if finished and all(e.get(field) is not None for e in finished)
                        else None
                    )
                row["cached_tokens"] = (
                    sum(cached)
                    if cached and all(v is not None for v in cached)
                    else None
                )
                row["cache_per_call"] = list(cached)
                row["provider_diagnostics"] = list(provider_diagnostics)
                report["cases"].append(row)
                report["summary"] = summarize(report["cases"])
                report["benchmark_summary"] = summarize(
                    [r for r in report["cases"] if r["id"] in BENCHMARK_IDS]
                )
                output.write_text(
                    json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False),
                    encoding="utf-8",
                )
                print(
                    f"{case['id']}: {row['veredito']}, {row['total_ms'] / 1000:.2f}s, cache={cached}",
                    flush=True,
                )
                if fatal:
                    print("Stopped: provider/deadline failure; no retry.", flush=True)
                    break
    finally:
        logger.removeHandler(capture)
        await client.close()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--case", action="append")
    parser.add_argument("--stable-tools", action="store_true")
    parser.add_argument("--interval", type=float, default=30)
    args = parser.parse_args()
    if not math.isfinite(args.interval) or args.interval < 0:
        parser.error("Interval must be finite and nonnegative.")
    # Snapshot benchmarking uses the same local credentials/database without copying them.
    configured_root = Path(os.getenv("CINEDATA_BENCHMARK_ROOT", ROOT))
    load_dotenv(configured_root / ".env")
    database = Path(os.getenv("DATABASE_PATH", "cinerocket (1).db"))
    if not database.is_absolute():
        database = configured_root / database
    cases = load_cases()
    if args.case:
        unknown = set(args.case) - {c["id"] for c in cases}
        if unknown:
            parser.error(f"Unknown cases: {sorted(unknown)}")
        cases = [c for c in cases if c["id"] in args.case]
    elif not args.all:
        cases = select_benchmark_cases(cases)
    report = asyncio.run(
        benchmark(
            cases,
            database,
            args.output,
            interval=args.interval,
            stable_tools=args.stable_tools,
        )
    )
    return (
        0
        if len(report["cases"]) == len(cases)
        and all(row["veredito"] == "correto" for row in report["cases"])
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
