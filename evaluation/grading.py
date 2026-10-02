"""Comparação de evidências, independente da execução e do provedor."""

import math

from app.database import QueryEvidence


def compare_rows(actual: QueryEvidence, expected: QueryEvidence, *, ordered: bool,
                 abs_tol: float = 0.01, rel_tol: float = 1e-9) -> bool:
    if actual.truncado or expected.truncado or len(actual.linhas) != len(expected.linhas):
        return False
    if len(actual.colunas) < len(expected.colunas):
        return False
    if len(set(actual.colunas)) != len(actual.colunas) or len(set(expected.colunas)) != len(expected.colunas):
        return False
    # Mesmos aliases permitem reordenar colunas; aliases diferentes mantêm a posição.
    if set(expected.colunas) <= set(actual.colunas):
        indices = [actual.colunas.index(name) for name in expected.colunas]
    elif len(actual.colunas) == len(expected.colunas):
        indices = list(range(len(expected.colunas)))
    else:
        return False
    if any(len(row) != len(actual.colunas) for row in actual.linhas) or any(len(row) != len(expected.colunas) for row in expected.linhas):
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
    # comparação quadrática limitada a 100 linhas; indexar se esse limite crescer.
    remaining = list(rows)
    for row in expected.linhas:
        match = next((i for i, candidate in enumerate(remaining) if same_row(candidate, row)), None)
        if match is None:
            return False
        remaining.pop(match)
    return True


def grade(case: dict, references: list[QueryEvidence], obtained: dict) -> tuple[bool, bool]:
    status_ok = obtained["answer"]["status"] == case["status_esperado"]
    if case["status_esperado"] in ("esclarecimento", "recusa"):
        return status_ok, True  # Motivo do esclarecimento/recusa ainda requer revisão manual.
    actual = [QueryEvidence(**query) for query in obtained["consultas"]]
    for reference in references:
        matched = False
        for query in actual:
            aliases = case.get("aliases", {})
            query = QueryEvidence(query.sql,query.parametros,[aliases.get(name,name) for name in query.colunas],
                                  query.linhas,query.truncado)
            wanted = case.get("colunas_relevantes", reference.colunas)
            # Chaves não são obrigatórias no ranking; quando presentes, também são conferidas.
            selected = [
                i for i,name in enumerate(reference.colunas)
                if name in wanted or (name.endswith("_id") and name in query.colunas)
            ]
            expected = QueryEvidence(reference.sql,reference.parametros,[reference.colunas[i] for i in selected],
                                     [[row[i] for i in selected] for row in reference.linhas],reference.truncado)
            candidate = query
            if not set(expected.colunas) <= set(query.colunas):
                # Ignorar chaves extras antes do fallback por posição permite aliases equivalentes.
                keep = [i for i,name in enumerate(query.colunas) if not name.endswith("_id") or name in expected.colunas]
                candidate = QueryEvidence(query.sql,query.parametros,[query.colunas[i] for i in keep],
                                          [[row[i] for i in keep] for row in query.linhas],query.truncado)
            if compare_rows(candidate,expected,ordered=case["ordenado"],abs_tol=case["abs_tol"],rel_tol=case["rel_tol"]):
                matched = True
                break
        if not matched:
            return status_ok, False
    return status_ok, True
