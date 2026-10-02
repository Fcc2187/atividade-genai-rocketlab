"""Dados sintéticos separados por cenário; nunca escrevem na base original."""

from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile

from app import database
from evaluation import run


def prepare_database(test_case):
    test_case.temporary = tempfile.TemporaryDirectory(prefix="cinedata-")
    test_case.addCleanup(test_case.temporary.cleanup)
    test_case.path = Path(test_case.temporary.name) / "banco com espaços # %.db"
    with closing(sqlite3.connect(test_case.path)) as connection, connection:
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
    test_case.db = database

def prepare_analytics(test_case):
    test_case.temporary = tempfile.TemporaryDirectory(prefix="cinedata-references-")
    test_case.addCleanup(test_case.temporary.cleanup)
    test_case.path = Path(test_case.temporary.name) / "analitico.db"
    with closing(sqlite3.connect(test_case.path)) as c, c:
        c.executescript("""
            CREATE TABLE dim_movies (sk_movie_id TEXT PRIMARY KEY, titulo TEXT, data_lancamento TEXT, ano_lancamento INTEGER);
            CREATE TABLE fact_movies_performance (sk_movie_id TEXT PRIMARY KEY, receita_usd REAL, orcamento_usd REAL, lucro_usd REAL, receita_brl REAL, orcamento_brl REAL, lucro_brl REAL, nota_imdb REAL, nota_tmdb REAL, popularidade REAL);
            CREATE TABLE dim_genres (sk_genre_id TEXT PRIMARY KEY, nome_genero TEXT);
            CREATE TABLE bridge_movie_genre (sk_movie_id TEXT, sk_genre_id TEXT, PRIMARY KEY(sk_movie_id,sk_genre_id));
            CREATE TABLE dim_people (sk_person_id TEXT PRIMARY KEY, nome_pessoa TEXT, tipo_pessoa TEXT);
            CREATE TABLE bridge_movie_person (sk_movie_id TEXT, sk_person_id TEXT, PRIMARY KEY(sk_movie_id,sk_person_id));
            CREATE TABLE dim_companies (sk_company_id TEXT PRIMARY KEY, nome_produtora TEXT);
            CREATE TABLE bridge_movie_company (sk_movie_id TEXT, sk_company_id TEXT, PRIMARY KEY(sk_movie_id,sk_company_id));
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
            INSERT INTO dim_companies VALUES ('c1','Produtora');
            INSERT INTO bridge_movie_company VALUES ('a','c1'),('b','c1'),('c','c1'),('d','c1'),('e','c1');
        """)
    test_case.evaluation = run

def query_reference(test_case, case_id):
    from app.database import execute_readonly
    case = next(case for case in test_case.evaluation.load_cases() if case["id"] == case_id)
    reference = case["referencias"][0]
    return execute_readonly(test_case.path, reference["sql"], reference["parametros"])


def model_answer(status="resultado"):
    return ("answer", {"status": status, "resposta": "Resposta baseada nas evidências.", "avisos": []})
