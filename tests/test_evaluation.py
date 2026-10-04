import json
import os
import unittest
from unittest.mock import AsyncMock, patch
from tests.helpers import prepare_database, prepare_analytics, query_reference
from evaluation import run
from evaluation.grading import compare_rows, grade


class EvaluationGradingTests(unittest.TestCase):
    def setUp(self):
        prepare_analytics(self)

    def test_poster_extra_nao_altera_metrica_e_identidade(self):
        from dataclasses import asdict
        from app.database import QueryEvidence
        case = next(c for c in self.evaluation.load_cases() if c['id'] == '01_receita_brl')
        reference = QueryEvidence('ref', {}, ['sk_movie_id', 'titulo', 'receita_brl'], [['a', 'Home', 500.0]], False)
        query = QueryEvidence('sql', {}, ['sk_movie_id', 'titulo', 'receita_brl', 'url_poster'], [['a', 'Home', 500.0, None]], False)
        def obtained():
            return {'answer': {'status': 'resultado'}, 'consultas': [asdict(query)]}
        self.assertEqual(grade(case, [reference], obtained()), (True, True))
        query.linhas[0][2] = 501.0
        self.assertEqual(grade(case, [reference], obtained()), (True, False))
        query.linhas[0][2] = 500.0
        query.linhas[0][0] = 'b'
        self.assertEqual(grade(case, [reference], obtained()), (True, False))

    def test_alias_financeiro_e_amostra(self):
        from dataclasses import asdict
        from app.database import QueryEvidence
        for case_id, aliases, indices, metric in [('11_produtora_lucro', ['nome_produtora','total_lucro_usd','qtd_filmes'], [1,2,3], 1),
                                                  ('11_produtora_lucro', ['nome_produtora','lucro_total_usd','qtd_filmes'], [1,2,3], 1),
                                                  ('12_margem_genero', ['qtd_filmes','genero','margem_media'], [3,1,2], 2)]:
            case = next(c for c in self.evaluation.load_cases() if c['id']==case_id)
            reference = query_reference(self, case_id)
            query = QueryEvidence('SQL equivalente', {}, aliases, [[r[i] for i in indices] for r in reference.linhas], False)
            obtained = {'answer':{'status':'resultado'},'consultas':[asdict(query)]}
            self.assertEqual(grade(case,[reference],obtained),(True,True))
            query.linhas[0][metric] += 1
            obtained['consultas'] = [asdict(query)]
            self.assertEqual(grade(case,[reference],obtained),(True,False))
        query = QueryEvidence('SQL sem amostra', {}, ['genero','margem_media'], [r[1:3] for r in reference.linhas], False)
        obtained['consultas'] = [asdict(query)]
        self.assertEqual(grade(case,[reference],obtained),(True,False))

    def test_comparador_ignora_sql_e_respeita_ordem(self):
        from app.database import QueryEvidence
        expected = QueryEvidence("sql de referência", {}, ["id", "valor"], [["a", 1.0], ["b", 2.0]], False)
        actual = QueryEvidence("sql diferente", {}, ["valor", "id"], [[2.00001, "b"], [1.00001, "a"]], False)
        compare = compare_rows
        self.assertTrue(compare(actual, expected, ordered=False, abs_tol=0.01, rel_tol=1e-9))
        self.assertFalse(compare(actual, expected, ordered=True, abs_tol=0.01, rel_tol=1e-9))
        incorrect = QueryEvidence("outro sql", {}, ["id", "valor"], [["a", 3.0], ["b", 2.0]], False)
        self.assertFalse(compare(incorrect, expected, ordered=True, abs_tol=0.01, rel_tol=1e-9))
        missing = QueryEvidence("outro sql", {}, ["id", "valor"], [["a", 1.0]], False)
        self.assertFalse(compare(missing, expected, ordered=False, abs_tol=0.01, rel_tol=1e-9))
        truncated = QueryEvidence("outro sql", {}, expected.colunas, expected.linhas, True)
        self.assertFalse(compare(truncated, expected, ordered=True, abs_tol=0.01, rel_tol=1e-9))
        precise = QueryEvidence('ref', {}, ['ano_lancamento','nota_media_imdb'], [[2026,6.338046141990175]], False)
        rounded = QueryEvidence('SQL arredondado', {}, precise.colunas, [[2026,6.34]], False)
        self.assertFalse(compare(rounded, precise, ordered=True, abs_tol=1e-6, rel_tol=1e-9))

    def test_comparador_colunas_relevantes_e_extras(self):
        from app.database import QueryEvidence
        expected=QueryEvidence("ref",{},["titulo","receita_brl"],[["Filme",100.0]],False)
        actual=QueryEvidence("outro SQL",{},["titulo","receita_brl","ano_lancamento"],[["Filme",100,2026]],False)
        self.assertTrue(compare_rows(actual,expected,ordered=True))
        wrong=QueryEvidence("outro SQL",{},actual.colunas,[["Filme",200,2026]],False)
        self.assertFalse(compare_rows(wrong,expected,ordered=True))
        missing=QueryEvidence("outro SQL",{},["titulo"],[["Filme"]],False)
        self.assertFalse(compare_rows(missing,expected,ordered=True))

    def test_alias_de_metrica_com_colunas_extras(self):
        from dataclasses import asdict
        from app.database import QueryEvidence
        case = next(c for c in self.evaluation.load_cases() if c['id'] == '03_maior_margem')
        reference = query_reference(self, case['id'])
        query = QueryEvidence('SQL equivalente', {}, ['titulo','receita_usd','margem'], [['A',100,60.0]], False)
        obtained = {'answer':{'status':'resultado'}, 'consultas':[asdict(query)]}
        self.assertEqual(grade(case,[reference],obtained), (True,True))
        query.linhas[0][-1] = 61.0
        obtained['consultas'] = [asdict(query)]
        self.assertEqual(grade(case,[reference],obtained), (True,False))
        director = next(c for c in self.evaluation.load_cases() if c['id'] == '08_diretor_nota')
        reference = query_reference(self, director['id'])
        query = QueryEvidence('SQL equivalente', {}, ['diretor','qtd_filmes','media_imdb','media_tmdb'],
                              [['Diretor Cinco',5,8.0,0.0]], False)
        obtained['consultas'] = [asdict(query)]
        self.assertEqual(grade(director,[reference],obtained), (True,True))
        query.colunas[2] = 'media_nota_imdb'
        obtained['consultas'] = [asdict(query)]
        self.assertEqual(grade(director,[reference],obtained), (True,True))
        query.linhas.append(['Outro Diretor',5,7.0,0.0])
        obtained['consultas'] = [asdict(query)]
        self.assertEqual(grade(director,[reference],obtained), (True,False))
        actor = next(c for c in self.evaluation.load_cases() if c['id'] == '07_ator_cinco_anos')
        reference = query_reference(self, actor['id'])
        query = QueryEvidence('SQL equivalente', {}, ['nome_pessoa','qtd_filmes','sk_person_id'],
                              [['Ator A',3,'p3']], False)
        obtained['consultas'] = [asdict(query)]
        self.assertEqual(grade(actor,[reference],obtained), (True,True))
        query.linhas[0][1] = 4
        obtained['consultas'] = [asdict(query)]
        self.assertEqual(grade(actor,[reference],obtained), (True,False))
        genre = next(c for c in self.evaluation.load_cases() if c['id'] == '02_lucro_genero')
        reference = query_reference(self, genre['id'])
        query = QueryEvidence('SQL equivalente', {}, ['genero','qtd_filmes','lucro_medio_usd'],
                              [[r[1],r[3],r[2]] for r in reference.linhas], False)
        obtained['consultas'] = [asdict(query)]
        self.assertEqual(grade(genre,[reference],obtained), (True,True))
        query.linhas[0][2] += 1
        obtained['consultas'] = [asdict(query)]
        self.assertEqual(grade(genre,[reference],obtained), (True,False))
        coverage = next(c for c in self.evaluation.load_cases() if c['id'] == '19_cobertura')
        reference = query_reference(self, coverage['id'])
        query = QueryEvidence('SQL equivalente', {}, ['genero','media_imdb','qtd_com_nota','total_filmes','proporcao'],
                              [[r[1],r[2],r[3],r[4],r[3]/r[4]] for r in reversed(reference.linhas)], False)
        obtained['consultas'] = [asdict(query)]
        self.assertEqual(grade(coverage,[reference],obtained), (True,True))
        query.linhas[0][2] += 1
        obtained['consultas'] = [asdict(query)]
        self.assertEqual(grade(coverage,[reference],obtained), (True,False))
        reviews = next(c for c in self.evaluation.load_cases() if c['id'] == '14_usuarios_imdb')
        reference = QueryEvidence('Referência', {}, ['sk_movie_id','titulo','nota_media_usuarios','nota_imdb','divergencia'],
                                  [['m1','A',2.0,8.0,6.0]], False)
        query = QueryEvidence('SQL equivalente', {}, ['titulo','id_filme','nota_media_usuarios','nota_imdb','diff'],
                              [[r[1],'id externo',r[2],r[3],r[4]] for r in reference.linhas], False)
        obtained['consultas'] = [asdict(query)]
        self.assertEqual(grade(reviews,[reference],obtained), (True,True))
        query.linhas[0][-1] += 1
        obtained['consultas'] = [asdict(query)]
        self.assertEqual(grade(reviews,[reference],obtained), (True,False))


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        prepare_database(self)
        self.evaluation = run
        from app.agent import AgentAnswer,QuestionResult
        self.output = self.path.with_suffix(".json")
        self.case={"id":"fake","categoria":"financeiro","pergunta":"Quantos filmes?","data_referencia":"2026-09-30",
              "status_esperado":"resultado","regras":[],"referencias":[{"sql":"SELECT COUNT(*) AS filmes FROM dim_movies","parametros":{}}],
              "ordenado":True,"abs_tol":0,"rel_tol":0}
        self.result=QuestionResult(AgentAnswer(status="resultado",resposta="Dois filmes.",avisos=[]),
                              [self.db.execute_readonly(self.path,self.case["referencias"][0]["sql"],{})],"simulado",
                              {"chamadas":2,"tokens_entrada":20,"tokens_saida":10,"tentativas_sql":1})

    def test_avaliacao_sem_api_por_padrao(self):
        with patch("app.agent.create_groq_model") as create,patch("evaluation.run.load_cases",return_value=[]):
            for flag in ([], ["--references-only"]):
                with self.subTest(flag=flag):
                    self.evaluation.main(flag+["--database",str(self.path),"--output",str(self.output)])
            create.assert_not_called()

    def test_relatorio_do_modelo_simulado_e_erros(self):
        from app.agent import ProviderUnavailable
        from app.agent import InvalidAgentResult
        from pydantic_ai.exceptions import ModelHTTPError
        rejected=InvalidAgentResult('Resposta inválida.')
        rejected.__cause__=ModelHTTPError(400,'openai/gpt-oss-120b',{'code':'tool_use_failed','message':'gsk-test','failed_generation':'privado'})
        for outcome,expected in [(self.result,"correto"),(ProviderUnavailable("offline"),"erro"),(rejected,"erro")]:
            with self.subTest(expected=expected,outcome=type(outcome).__name__),patch.dict(os.environ,{"MODEL_PROVIDER":"groq","GROQ_API_KEY":"gsk-test","MODEL_RUNTIME":"Groq API"}),patch("evaluation.run.load_cases",return_value=[self.case]),patch("app.agent.create_groq_model",return_value=(object(),AsyncMock())):
                with patch("app.agent.responder",new_callable=AsyncMock) as respond:
                    if isinstance(outcome,Exception):respond.side_effect=outcome
                    else:respond.return_value=outcome
                    self.evaluation.main(["--smoke","--database",str(self.path),"--output",str(self.output)])
                    report=json.loads(self.output.read_text(encoding="utf-8"))
                    self.assertEqual(report["runtime_configurado"],"Groq API")
                    self.assertEqual(report["casos"][0]["veredito"],expected)
                    self.assertLessEqual(respond.call_count,1)
                    if outcome is rejected:
                        self.assertEqual(report['casos'][0]['erro_provedor'],{'status':400,'codigo':'tool_use_failed','mensagem':'[REDACTED]'})
                        self.assertNotIn('privado',json.dumps(report))

    def test_intervalo_entre_perguntas(self):
        with patch.dict(os.environ,{"MODEL_PROVIDER":"groq","GROQ_API_KEY":"gsk-test"}),patch("evaluation.run.load_cases",return_value=[self.case,self.case]),patch("app.agent.create_groq_model",return_value=(object(),AsyncMock())):
            with patch("app.agent.responder",new_callable=AsyncMock,return_value=self.result),patch("evaluation.run.asyncio.sleep",new_callable=AsyncMock) as pause:
                self.evaluation.main(["--all","--interval","60","--database",str(self.path),"--output",str(self.output)])
                pause.assert_awaited_once_with(60)

    def test_smoke_seleciona_cinco_categorias(self):
        cases=self.evaluation.select_cases(self.evaluation.load_cases(),smoke=True)
        self.assertEqual(len(cases),5)
        self.assertEqual(len({c["categoria"] for c in cases}),5)

    def test_relatorio_identifica_fontes_do_agente_e_prompt(self):
        import hashlib
        with patch.dict(os.environ,{"MODEL_PROVIDER":"groq","GROQ_API_KEY":"gsk-test"}),patch("evaluation.run.load_cases",return_value=[self.case]),patch("app.agent.create_groq_model",return_value=(object(),AsyncMock())):
            with patch("app.agent.responder",new_callable=AsyncMock,return_value=self.result):
                self.evaluation.main(["--smoke","--database",str(self.path),"--output",str(self.output)])
        report=json.loads(self.output.read_text(encoding="utf-8"))
        self.assertIn("codigo_prompts_sha256",report)
        for key,filename in (("codigo_agente_sha256","agent.py"),("codigo_prompts_sha256","prompts.py")):
            with self.subTest(source=filename):
                expected=hashlib.sha256((run.ROOT / "app" / filename).read_bytes()).hexdigest()
                self.assertEqual(report[key],expected)

    def test_prazo_avaliacao_invalido(self):
        with patch("evaluation.run.load_cases",return_value=[]):
            for timeout in ["0","-1","nan","inf"]:
                with self.subTest(timeout=timeout),self.assertRaises(SystemExit):
                    self.evaluation.main(["--smoke","--timeout",timeout])
            for interval in ["-1","nan","inf"]:
                with self.subTest(interval=interval),self.assertRaises(SystemExit):
                    self.evaluation.main(["--all","--interval",interval])
