from datetime import date
import unittest

from app.prompts import build_instructions


class PromptTests(unittest.TestCase):
    def test_rules_precede_schema_and_variable_reference_date(self):
        prompt = build_instructions("SCHEMA-A", date(2026, 10, 5))
        self.assertTrue(prompt.startswith("Você é um analista do catálogo CineData."))
        self.assertLess(prompt.index("Confira período"), prompt.index("Esquema real:"))
        self.assertLess(prompt.index("SCHEMA-A"), prompt.index("2026-10-05"))
        updated = build_instructions("SCHEMA-B", date(2026, 10, 6))
        self.assertEqual(
            prompt.split("Esquema real:")[0], updated.split("Esquema real:")[0]
        )
