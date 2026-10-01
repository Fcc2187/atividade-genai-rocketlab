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


class AnalyticalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="cinedata-references-")
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "analitico.db"
        with closing(sqlite3.connect(self.path)) as c, c:
            c.executescript("""
                CREATE TABLE dim_movies (sk_movie_id TEXT PRIMARY KEY, titulo TEXT, data_lancamento TEXT, ano_lancamento INTEGER);
                CREATE TABLE fact_movies_performance (sk_movie_id TEXT PRIMARY KEY, receita_usd REAL, orcamento_usd REAL, lucro_usd REAL, receita_brl REAL, orcamento_brl REAL, lucro_brl REAL, nota_imdb REAL, nota_tmdb REAL, popularidade REAL);
                CREATE TABLE dim_genres (sk_genre_id TEXT PRIMARY KEY, nome_genero TEXT);
                CREATE TABLE bridge_movie_genre (sk_movie_id TEXT, sk_genre_id TEXT, PRIMARY KEY(sk_movie_id,sk_genre_id));
                CREATE TABLE dim_people (sk_person_id TEXT PRIMARY KEY, nome_pessoa TEXT, tipo_pessoa TEXT);
                CREATE TABLE bridge_movie_person (sk_movie_id TEXT, sk_person_id TEXT, PRIMARY KEY(sk_movie_id,sk_person_id));
                INSERT INTO dim_movies VALUES ('a','A','2021-09-30',2021), ('b','B','2026-09-30',2026), ('c','C','2026-10-01',2026), ('d','D','2021-09-29',2021), ('e','E','2026-09-29',2026);
                INSERT INTO fact_movies_performance VALUES
                    ('a',100,40,60,500,200,300,8,7,10),
                    ('b',NULL,20,-20,NULL,100,-100,8,7,100),
                    ('c',100,NULL,100,500,NULL,500,8,7,1),
                    ('d',0,10,-10,0,50,-50,8,7,1),
                    ('e',200,100,100,1000,500,500,8,7,2);
                INSERT INTO dim_genres VALUES ('g1','Action'), ('g2','Adventure');
                INSERT INTO bridge_movie_genre VALUES ('a','g1'), ('b','g1'), ('c','g1'), ('d','g1'), ('e','g1'), ('a','g2');
                INSERT INTO dim_people VALUES ('p1','Diretor Cinco','Diretor'), ('p2','Diretor Quatro','Diretor'), ('p3','Ator A','Ator');
                INSERT INTO bridge_movie_person VALUES ('a','p1'), ('b','p1'), ('c','p1'), ('d','p1'), ('e','p1'), ('a','p2'), ('b','p2'), ('c','p2'), ('d','p2'), ('a','p3'), ('b','p3'), ('c','p3'), ('d','p3'), ('e','p3');
            """)
        try:
            self.evaluation = importlib.import_module("evaluation.run")
        except ModuleNotFoundError as error:
            self.fail(f"Avaliação ainda ausente: {error.name}")

    def reference(self, case_id):
        from app.database import execute_readonly
        case = next(case for case in self.evaluation.load_cases() if case["id"] == case_id)
        reference = case["referencias"][0]
        return execute_readonly(self.path, reference["sql"], reference["parametros"])

    def test_join_nao_duplica_receita(self):
        result = self.reference("10_filmes_genero")
        self.assertEqual(result.linhas, [["g1", "Action", 5], ["g2", "Adventure", 1]])
        finance = self.reference("02_lucro_genero")
        self.assertEqual(finance.linhas, [["g1", "Action", 62.5, 4], ["g2", "Adventure", 60.0, 1]])

    def test_lucro_e_margem_com_nulos(self):
        self.assertEqual(self.reference("03_maior_margem").linhas, [["a", "A", 60.0]])
        self.assertEqual(self.reference("12_margem_genero").linhas, [["g2", "Adventure", 60.0, 1], ["g1", "Action", 55.0, 2]])

    def test_diretor_minimo_cinco_filmes(self):
        self.assertEqual(self.reference("08_diretor_nota").linhas, [["p1", "Diretor Cinco", 8.0, 5]])

    def test_datas_ano_e_janela_movel(self):
        self.assertEqual(self.reference("07_ator_cinco_anos").linhas, [["p3", "Ator A", 3]])
        self.assertEqual(self.reference("20_anos_parciais").linhas, [[2026, 2]])
        self.assertEqual(self.reference("21_futuros").linhas, [[1]])

    def test_comparador_ignora_sql_e_respeita_ordem(self):
        from app.database import QueryEvidence
        expected = QueryEvidence("sql de referência", {}, ["id", "valor"], [["a", 1.0], ["b", 2.0]], False)
        actual = QueryEvidence("sql diferente", {}, ["valor", "id"], [[2.00001, "b"], [1.00001, "a"]], False)
        compare = self.evaluation.compare_rows
        self.assertTrue(compare(actual, expected, ordered=False, abs_tol=0.01, rel_tol=1e-9))
        self.assertFalse(compare(actual, expected, ordered=True, abs_tol=0.01, rel_tol=1e-9))
        incorrect = QueryEvidence("outro sql", {}, ["id", "valor"], [["a", 3.0], ["b", 2.0]], False)
        self.assertFalse(compare(incorrect, expected, ordered=True, abs_tol=0.01, rel_tol=1e-9))
        missing = QueryEvidence("outro sql", {}, ["id", "valor"], [["a", 1.0]], False)
        self.assertFalse(compare(missing, expected, ordered=False, abs_tol=0.01, rel_tol=1e-9))
        truncated = QueryEvidence("outro sql", {}, expected.colunas, expected.linhas, True)
        self.assertFalse(compare(truncated, expected, ordered=True, abs_tol=0.01, rel_tol=1e-9))


if __name__ == "__main__":
    unittest.main()
