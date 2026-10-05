import unittest
from evaluation import benchmark

from evaluation.benchmark import summarize, select_benchmark_cases
from evaluation.run import load_cases


class BenchmarkTests(unittest.TestCase):
    def test_rate_limit_dimension_only_exports_known_unambiguous_enum(self):
        for dimension in ("TPM", "TPD", "RPM", "RPD", "ITPM", "OTPM"):
            self.assertEqual(
                benchmark.rate_limit_dimension(
                    f"SECRET organization ({dimension}): Requested 4548"
                ),
                dimension,
            )
        for value in (None, 123, {}, "SECRET unknown limit", "(TPM) and (TPD)"):
            self.assertIsNone(benchmark.rate_limit_dimension(value))

    def test_representative_selection_covers_ten_questions(self):
        cases = select_benchmark_cases(load_cases())
        self.assertEqual(len(cases), 10)
        self.assertEqual(len({c["id"] for c in cases}), 10)
        self.assertIn("15_sem_dados", {c["id"] for c in cases})
        self.assertIn("09_par_ator_diretor", {c["id"] for c in cases})

    def test_summary_uses_nearest_rank_p95_and_reports_failures(self):
        rows = [{"total_ms": n * 1000, "veredito": "correto"} for n in range(1, 11)]
        rows.append({"total_ms": 999999, "veredito": "erro"})
        result = summarize(rows)
        self.assertEqual(result["successful_cases"], 10)
        self.assertEqual(result["errors"], 1)
        self.assertEqual(
            result["total_ms"], {"mean": 5500, "median": 5500, "p95": 10000}
        )

    def test_empty_summary_does_not_invent_measurements(self):
        result = summarize([])
        self.assertEqual(result["successful_cases"], 0)
        self.assertIsNone(result["total_ms"])
