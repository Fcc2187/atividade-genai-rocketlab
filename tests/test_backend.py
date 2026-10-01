import hashlib
from contextlib import closing
import importlib
import json
import math
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="cinedata-")
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "banco com espaços # %.db"
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.executescript("""
                CREATE TABLE dim_movies (sk_movie_id TEXT PRIMARY KEY, titulo TEXT);
                CREATE TABLE fact_movies_performance (
                    sk_movie_id TEXT PRIMARY KEY REFERENCES dim_movies,
                    receita_usd REAL, orcamento_usd REAL, lucro_usd REAL);
                CREATE TABLE alembic_version (version_num TEXT);
                INSERT INTO dim_movies VALUES ('a', 'O''Brien'), ('b', 'Outro');
                INSERT INTO fact_movies_performance VALUES ('a', 100, 40, 60), ('b', NULL, 20, -20);
                INSERT INTO alembic_version VALUES ('privado');
            """)
        try:
            self.db = importlib.import_module("app.database")
        except ModuleNotFoundError as error:
            self.fail(f"Ferramenta ainda ausente: {error.name}")

    def test_caminho_com_espacos_e_banco_ausente(self):
        result = self.db.execute_readonly(self.path, "SELECT titulo FROM dim_movies ORDER BY sk_movie_id", {})
        self.assertEqual(result.linhas, [["O'Brien"], ["Outro"]])
        absent = self.path.with_name("ausente.db")
        with self.assertRaises(self.db.DatabaseUnavailable):
            self.db.execute_readonly(absent, "SELECT 1", {})
        self.assertFalse(absent.exists())

    def test_select_cte_e_parametros(self):
        result = self.db.execute_readonly(self.path, "WITH filmes AS (SELECT * FROM dim_movies) SELECT titulo AS filme FROM filmes WHERE titulo = :titulo", {"titulo": "O'Brien"})
        self.assertEqual(result.colunas, ["filme"])
        self.assertEqual(result.linhas, [["O'Brien"]])
        self.assertEqual(result.parametros, {"titulo": "O'Brien"})
        self.assertFalse(result.truncado)
        self.assertEqual(self.db.execute_readonly(self.path, "SELECT COUNT(*) AS n FROM dim_movies", {}).linhas, [[2]])
        self.assertEqual(self.db.execute_readonly(self.path, "SELECT COUNT(*) FROM (SELECT titulo FROM dim_movies)", {}).linhas, [[2]])
        self.assertEqual(self.db.execute_readonly(self.path, "SELECT SUM(receita_usd), AVG(lucro_usd) FROM fact_movies_performance", {}).linhas, [[100.0, 20.0]])

    def test_bloqueia_operacoes_indevidas(self):
        original = hashlib.sha256(self.path.read_bytes()).hexdigest()
        statements = [
            "DELETE FROM dim_movies", "INSERT INTO dim_movies VALUES ('x', 'x')",
            "UPDATE dim_movies SET titulo='x'", "CREATE TABLE dano (x)",
            "DROP TABLE dim_movies", "ATTACH DATABASE ':memory:' AS externo",
            "PRAGMA journal_mode=WAL", "PRAGMA table_info(dim_movies)",
            "SELECT load_extension('x')", "SELECT randomblob(999999999)",
            "SELECT version_num FROM alembic_version", "SELECT name FROM sqlite_master",
            "SELECT name FROM pragma_table_info('dim_movies')", "BEGIN",
            "SELECT * FROM dim_movies; DELETE FROM dim_movies",
            "WITH filmes AS (SELECT 1) DELETE FROM dim_movies",
            "CREATE TEMP TABLE dano (x)",
        ]
        for sql in statements:
            with self.subTest(sql=sql), self.assertRaises(self.db.QueryRejected):
                self.db.execute_readonly(self.path, sql, {})
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), original)
        self.assertEqual(self.db.execute_readonly(self.path, "SELECT COUNT(*) FROM dim_movies", {}).linhas, [[2]])

    def test_timeout_e_truncamento(self):
        forever = "WITH RECURSIVE numeros(n) AS (VALUES(1) UNION ALL SELECT n+1 FROM numeros) SELECT SUM(n) FROM numeros"
        started = time.monotonic()
        with self.assertRaises(self.db.QueryTimedOut):
            self.db.execute_readonly(self.path, forever, {}, timeout_seconds=0.02)
        self.assertLess(time.monotonic() - started, 2)
        with self.assertRaises(self.db.QueryTimedOut):
            self.db.execute_readonly(self.path, "SELECT 1", {}, deadline=time.monotonic() - 1)
        rows = self.db.execute_readonly(self.path, "WITH RECURSIVE numeros(n) AS (VALUES(1) UNION ALL SELECT n+1 FROM numeros WHERE n<101) SELECT n FROM numeros", {})
        self.assertEqual(len(rows.linhas), 100)
        self.assertEqual(rows.linhas[-1], [100])
        self.assertTrue(rows.truncado)
        text = self.db.execute_readonly(self.path, "SELECT :texto AS texto", {"texto": "🌠" * 15000})
        self.assertTrue(text.truncado)
        self.assertLessEqual(len(json.dumps({"colunas": text.colunas, "linhas": text.linhas}, ensure_ascii=False)), 12000)
        self.assertTrue(text.linhas)

    def test_banco_corrompido_e_tabela_tecnica(self):
        damaged = self.path.with_name("corrompido.db")
        damaged.write_text("isto não é SQLite", encoding="utf-8")
        with self.assertRaises(self.db.DatabaseUnavailable):
            self.db.read_schema(damaged)
        with self.assertRaises(self.db.DatabaseUnavailable):
            self.db.execute_readonly(damaged, "SELECT * FROM dim_movies", {})
        schema = self.db.read_schema(self.path)
        self.assertIn("sk_movie_id", schema)
        self.assertIn("REFERENCES", schema)
        self.assertNotIn("alembic_version", schema)

    def test_sql_invalido_e_parametros_invalidos(self):
        for sql, params in [("SELECT coluna_inexistente FROM dim_movies", {}), ("SELECT :valor", {})]:
            with self.subTest(sql=sql), self.assertRaises(self.db.QueryInvalid):
                self.db.execute_readonly(self.path, sql, params)
        for value in [math.nan, math.inf, True, [1], {"x": 1}, b"blob", 2**100]:
            with self.subTest(value=repr(value)), self.assertRaises(self.db.QueryInvalid):
                self.db.execute_readonly(self.path, "SELECT :valor", {"valor": value})
        for sql, params in [("", {}), ("SELECT 1 " * 1300, {}), ("SELECT 1", {str(i): i for i in range(51)})]:
            with self.subTest(size=len(sql)), self.assertRaises(self.db.QueryInvalid):
                self.db.execute_readonly(self.path, sql, params)


if __name__ == "__main__":
    unittest.main()
