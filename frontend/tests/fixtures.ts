import type { Answer } from '../src/types'

// Synthetic contract fixtures, never live model results.
export const rankingAnswer: Answer = {
  status: 'resultado', resposta: 'Avatar lidera a bilheteria entre os filmes disponíveis no catálogo.',
  avisos: ['Valores em USD, sem ajuste pela inflação. O ranking reflete a cobertura da base.'],
  consultas: [{ sql: 'SELECT titulo, ano_lancamento, url_poster, receita_usd FROM dim_movies JOIN fact_movies_performance USING (sk_movie_id) ORDER BY receita_usd DESC LIMIT :limite', parametros: { limite: 5 },
    colunas: ['titulo', 'ano_lancamento', 'url_poster', 'receita_usd'],
    linhas: [['Avatar', 2009, 'https://images.example.test/avatar.png', 2920000000], ['Vingadores: Ultimato', 2019, null, 2800000000], ['Avatar: O Caminho da Água', 2022, 'javascript:invalid', 2320000000], ['Titanic', 1997, 'https://images.example.test/missing.png', 2260000000], ['Star Wars: O Despertar da Força', 2015, null, 2070000000]], truncado: false }],
  modelo: 'modelo-de-teste', uso: { requests: 1, input_tokens: 42, output_tokens: 23 },
}
export const aggregateAnswer: Answer = { ...rankingAnswer, resposta: 'Contagem por gênero.', avisos: [], consultas: [{ sql: 'SELECT genero, total FROM exemplo', parametros: {}, colunas: ['genero', 'total'], linhas: [['Drama', 42], ['Comédia', 0], [null, 3], ['', -1]], truncado: false }] }
export const longAnswer: Answer = { ...rankingAnswer, resposta: 'Resposta longa. '.repeat(80), consultas: [{ ...rankingAnswer.consultas[0], linhas: [['Um título de filme muito longo que deve permanecer legível mesmo numa tela de 320 pixels', 2026, null, 123456789]], truncado: true }] }
export const statusAnswers = {
  resultado: rankingAnswer,
  esclarecimento: { ...rankingAnswer, status: 'esclarecimento', resposta: 'Você quer a bilheteria em USD ou em BRL?', avisos: [], consultas: [] },
  recusa: { ...rankingAnswer, status: 'recusa', resposta: 'Esta operação não é permitida no catálogo somente leitura.', avisos: [], consultas: [] },
  sem_dados: { ...rankingAnswer, status: 'sem_dados', resposta: 'Nenhum filme corresponde aos filtros.', avisos: [], consultas: [{ sql: 'SELECT titulo FROM dim_movies WHERE 1=0', parametros: {}, colunas: ['titulo'], linhas: [], truncado: false }] },
} satisfies Record<Answer['status'], Answer>
