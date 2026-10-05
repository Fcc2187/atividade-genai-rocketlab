"""Gabaritos SQL independentes do modelo; por padrão, só executa leituras locais."""

import argparse
import asyncio
from dataclasses import asdict
from datetime import date
import hashlib
import json
import math
import os
from pathlib import Path
import time

from dotenv import load_dotenv

from app.database import execute_readonly
from evaluation.grading import grade

ROOT = Path(__file__).resolve().parents[1]


def load_cases() -> list[dict]:
    return json.loads(
        Path(__file__).with_name("cases.json").read_text(encoding="utf-8")
    )


def select_cases(cases: list[dict], *, smoke: bool) -> list[dict]:
    if not smoke:
        return cases
    categories = set()
    selected = []
    for case in cases:
        if case["categoria"] not in categories and case["categoria"] != "seguranca":
            selected.append(case)
            categories.add(case["categoria"])
    return selected


async def evaluate(
    cases: list[dict],
    database: Path,
    timeout: float,
    output: Path,
    *,
    interval: float = 0,
):
    from app.agent import (
        InvalidAgentResult,
        ProviderRateLimited,
        ProviderRequestTooLarge,
        ProviderUnavailable,
        QuestionTimedOut,
        create_groq_model,
        responder,
    )
    from app.database import DatabaseUnavailable, QueryTimedOut
    from pydantic_ai.exceptions import ModelHTTPError

    if os.getenv("MODEL_PROVIDER", "groq") != "groq":
        raise ValueError("Somente Groq está integrado.")
    name = os.getenv("MODEL_NAME", "openai/gpt-oss-120b")
    model, client = create_groq_model(
        os.getenv("MODEL_BASE_URL", "https://api.groq.com/openai/v1"),
        name,
        os.getenv("GROQ_API_KEY", ""),
    )
    report = {
        "modelo": name,
        "provedor": "groq",
        "runtime_configurado": "Groq API",
        "codigo_agente_sha256": hashlib.sha256(
            (ROOT / "app" / "agent.py").read_bytes()
        ).hexdigest(),
        "codigo_cota_sha256": hashlib.sha256(
            (ROOT / "app" / "groq_quota.py").read_bytes()
        ).hexdigest(),
        "codigo_prompts_sha256": hashlib.sha256(
            (ROOT / "app" / "prompts.py").read_bytes()
        ).hexdigest(),
        "codigo_avaliador_sha256": hashlib.sha256(
            (ROOT / "evaluation" / "grading.py").read_bytes()
        ).hexdigest(),
        "quantizacao_configurada": None,
        "contexto_configurado": None,
        "prazo_segundos": timeout,
        "intervalo_segundos": interval,
        "explicacoes": "Requerem revisão manual; acerto automático avalia status e linhas.",
        "casos": [],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        for index, case in enumerate(cases):
            if index and interval:
                print(
                    f"Intervalo solicitado entre perguntas: {interval:g} s.", flush=True
                )
                await asyncio.sleep(interval)
            expected = [
                await asyncio.to_thread(
                    execute_readonly, database, ref["sql"], ref["parametros"]
                )
                for ref in case["referencias"]
            ]
            if any(item.truncado for item in expected):
                raise ValueError(f"Referência truncada: {case['id']}")
            item = {
                "id": case["id"],
                "pergunta": case["pergunta"],
                "categoria": case["categoria"],
                "data_referencia": case["data_referencia"],
                "status_esperado": case["status_esperado"],
                "esperado": [asdict(e) for e in expected],
            }
            start = time.monotonic()
            fatal = False
            print(f"Iniciando {case['id']}...", flush=True)
            try:
                result = await responder(
                    case["pergunta"],
                    database,
                    date.fromisoformat(case["data_referencia"]),
                    model,
                    timeout_seconds=timeout,
                )
                item["obtido"] = asdict(result)
                item["obtido"]["answer"] = result.answer.model_dump()
                status_ok, rows_ok = grade(case, expected, item["obtido"])
                item["veredito"] = "correto" if status_ok and rows_ok else "incorreto"
                item["status_correto"], item["linhas_corretas"] = status_ok, rows_ok
            except (
                ProviderUnavailable,
                ProviderRateLimited,
                ProviderRequestTooLarge,
                QuestionTimedOut,
                InvalidAgentResult,
                DatabaseUnavailable,
                QueryTimedOut,
            ) as error:
                item["veredito"], item["erro"] = "erro", type(error).__name__
                item["diagnostico"] = str(error)
                if isinstance(error.__cause__, ModelHTTPError):
                    cause = error.__cause__
                    body = cause.body if isinstance(cause.body, dict) else {}
                    body = body.get("error", body)
                    if isinstance(body, dict):
                        key = os.getenv("GROQ_API_KEY", "")
                        message = str(body.get("message", ""))
                        if key:
                            message = message.replace(key, "[REDACTED]")
                        item["erro_provedor"] = {
                            "status": cause.status_code,
                            "codigo": str(body.get("code", ""))[:100],
                            "mensagem": message[:1000],
                        }
                fatal = isinstance(
                    error,
                    (
                        ProviderUnavailable,
                        ProviderRateLimited,
                        QuestionTimedOut,
                        DatabaseUnavailable,
                    ),
                )
            item["segundos"] = time.monotonic() - start
            item["memoria_processo"] = (
                None  # Inferência remota: memória do servidor não é medida aqui.
            )
            report["casos"].append(item)
            output.write_text(
                json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False),
                encoding="utf-8",
            )
            print(
                f"{case['id']}: {item['veredito']} em {item['segundos']:.2f} s",
                flush=True,
            )
            if fatal:
                print(
                    "Execução interrompida para diagnóstico; nenhum retry automático.",
                    flush=True,
                )
                break
    finally:
        await client.close()


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--references-only",
        action="store_true",
        help="Executa apenas SQL de referência (padrão).",
    )
    mode.add_argument(
        "--smoke", action="store_true", help="Cinco perguntas reais, uma por categoria."
    )
    mode.add_argument("--all", action="store_true", help="Todas as perguntas reais.")
    parser.add_argument("--database", type=Path)
    parser.add_argument(
        "--case",
        action="append",
        dest="case_ids",
        help="Restringe a IDs para verificar correções.",
    )
    parser.add_argument("--timeout", type=float)
    parser.add_argument(
        "--interval",
        type=float,
        default=0,
        help="Espera explícita entre perguntas para respeitar cotas; não repete chamadas.",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if not math.isfinite(args.interval) or args.interval < 0:
        parser.error("Intervalo deve ser finito e não negativo.")
    load_dotenv(ROOT / ".env")
    database = args.database or Path(os.getenv("DATABASE_PATH", "cinerocket (1).db"))
    if not database.is_absolute():
        database = ROOT / database
    cases = load_cases()
    if args.case_ids:
        unknown = set(args.case_ids) - {case["id"] for case in cases}
        if unknown:
            parser.error(f"Casos desconhecidos: {sorted(unknown)}")
        cases = [case for case in cases if case["id"] in args.case_ids]
    if args.smoke or args.all:
        timeout = (
            args.timeout
            if args.timeout is not None
            else float(os.getenv("QUESTION_TIMEOUT_SECONDS", "600"))
        )
        if not math.isfinite(timeout) or timeout <= 0:
            parser.error("Prazo deve ser finito e positivo.")
        asyncio.run(
            evaluate(
                select_cases(cases, smoke=args.smoke),
                database,
                timeout,
                args.output or ROOT / "runtime" / "model-results.json",
                interval=args.interval,
            )
        )
        return
    results = []
    for case in cases:
        evidence = [
            execute_readonly(database, ref["sql"], ref["parametros"])
            for ref in case["referencias"]
        ]
        if any(item.truncado for item in evidence):
            raise RuntimeError(f"Referência truncada: {case['id']}")
        results.append(
            {
                "id": case["id"],
                "status_esperado": case["status_esperado"],
                "consultas": [asdict(item) for item in evidence],
            }
        )
        print(
            f"{case['id']}: {sum(len(item.linhas) for item in evidence)} linhas; {case['status_esperado']}"
        )
    output = args.output or ROOT / "runtime" / "reference-results.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(
        json.dumps(results, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(
        f"Referências verificadas: {len(results)}. Arquivo: runtime/reference-results.json"
    )


if __name__ == "__main__":
    main()
