import unittest
from tests.helpers import prepare_analytics, prepare_rankings, query_reference


class AnalyticalTests(unittest.TestCase):
    def setUp(self):
        prepare_analytics(self)

    def test_join_nao_duplica_receita(self):
        result = query_reference(self, "10_filmes_genero")
        self.assertEqual(result.linhas, [["g1", "Action", 5], ["g2", "Adventure", 1]])
        finance = query_reference(self, "02_lucro_genero")
        self.assertEqual(
            finance.linhas, [["g1", "Action", 62.5, 4], ["g2", "Adventure", 60.0, 1]]
        )

    def test_lucro_e_margem_com_nulos(self):
        self.assertEqual(
            query_reference(self, "03_maior_margem").linhas, [["a", "A", 60.0]]
        )
        self.assertEqual(
            query_reference(self, "12_margem_genero").linhas,
            [["g2", "Adventure", 60.0, 1], ["g1", "Action", 55.0, 2]],
        )
        self.assertEqual(
            query_reference(self, "11_produtora_lucro").linhas,
            [["c1", "Produtora", 150.0, 3]],
        )

    def test_diretor_minimo_cinco_filmes(self):
        self.assertEqual(
            query_reference(self, "08_diretor_nota").linhas,
            [["p1", "Diretor Cinco", 8.0, 5]],
        )
        self.assertEqual(
            query_reference(self, "09_par_ator_diretor").linhas,
            [["p3", "Ator A", "p1", "Diretor Cinco", 5]],
        )

    def test_datas_ano_e_janela_movel(self):
        self.assertEqual(
            query_reference(self, "07_ator_cinco_anos").linhas, [["p3", "Ator A", 3]]
        )
        self.assertEqual(query_reference(self, "20_anos_parciais").linhas, [[2026, 2]])
        self.assertEqual(query_reference(self, "21_futuros").linhas, [[1]])


class ClosureRankingTests(unittest.TestCase):
    def setUp(self):
        prepare_rankings(self)

    def test_margem_top5_filtra_nulos_zero_e_limita_seis_elegiveis(self):
        self.assertEqual(
            query_reference(self, "23_margem_top5").linhas,
            [
                ["f", "F", 60.0],
                ["e", "E", 50.0],
                ["d", "D", 40.0],
                ["c", "C", 30.0],
                ["b", "B", 20.0],
            ],
        )

    def test_diretores_top5_conta_notas_validas_e_desempata_nome_chave(self):
        self.assertEqual(
            query_reference(self, "24_diretores_top5").linhas,
            [
                ["p0", "Alpha", 6.0, 5],
                ["p1", "Alpha", 6.0, 5],
                ["p2", "Bravo", 6.0, 5],
                ["p3", "Charlie", 6.0, 5],
                ["p4", "Delta", 6.0, 5],
            ],
        )

    def test_avaliacoes_top5_nao_usa_popularidade(self):
        self.assertEqual(
            query_reference(self, "25_avaliacoes_top5").linhas,
            [
                ["f", "F", 60],
                ["e", "E", 50],
                ["d", "D", 40],
                ["c", "C", 30],
                ["b", "B", 20],
            ],
        )
