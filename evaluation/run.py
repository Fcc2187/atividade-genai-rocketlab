"""Gabaritos SQL independentes do modelo; por padrão, só executa leituras locais."""

import argparse
from dataclasses import asdict
import json
import math
import os
from pathlib import Path

from dotenv import load_dotenv

from app.database import QueryEvidence, execute_readonly

ROOT = Path(__file__).resolve().parents[1]


def load_cases() -> list[dict]:
    return json.loads(Path(__file__).with_name("cases.json").read_text(encoding="utf-8"))


def compare_rows(actual: QueryEvidence, expected: QueryEvidence, *, ordered: bool,
                 abs_tol: float = 0.01, rel_tol: float = 1e-9) -> bool:
    if actual.truncado or expected.truncado or len(actual.linhas) != len(expected.linhas):
        return False
    if len(actual.colunas) != len(expected.colunas):
        return False
    if len(set(actual.colunas)) != len(actual.colunas) or len(set(expected.colunas)) != len(expected.colunas):
        return False
    # Mesmos aliases permitem reordenar colunas; aliases diferentes mantêm a posição.
    indices = ([actual.colunas.index(name) for name in expected.colunas]
               if set(actual.colunas) == set(expected.colunas) else list(range(len(expected.colunas))))
    if any(len(row) != len(actual.colunas) for row in actual.linhas + expected.linhas):
        return False
    rows = [[row[index] for index in indices] for row in actual.linhas]

    def same_row(left, right):
        return all(
            math.isclose(a, b, abs_tol=abs_tol, rel_tol=rel_tol)
            if isinstance(b, float) and type(a) in (int, float)
            else type(a) is type(b) and a == b
            for a, b in zip(left, right)
        )

    if ordered:
        return all(same_row(a, b) for a, b in zip(rows, expected.linhas))
    # ponytail: comparação quadrática limitada a 100 linhas; indexar se esse limite crescer.
    remaining = list(rows)
    for row in expected.linhas:
        match = next((i for i, candidate in enumerate(remaining) if same_row(candidate, row)), None)
        if match is None:
            return False
        remaining.pop(match)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--references-only", action="store_true", help="Executa apenas SQL de referência (padrão).")
    parser.add_argument("--database", type=Path)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    database = args.database or Path(os.getenv("DATABASE_PATH", "cinerocket (1).db"))
    if not database.is_absolute():
        database = ROOT / database
    results = []
    for case in load_cases():
        evidence = [execute_readonly(database, ref["sql"], ref["parametros"]) for ref in case["referencias"]]
        if any(item.truncado for item in evidence):
            raise RuntimeError(f"Referência truncada: {case['id']}")
        results.append({"id": case["id"], "status_esperado": case["status_esperado"],
                        "consultas": [asdict(item) for item in evidence]})
        print(f"{case['id']}: {sum(len(item.linhas) for item in evidence)} linhas; {case['status_esperado']}")
    output = ROOT / "runtime" / "reference-results.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Referências verificadas: {len(results)}. Arquivo: runtime/reference-results.json")


if __name__ == "__main__":
    main()
