import type { QuestionResponse } from '../src/types'

// Dados sintéticos com os campos do QuestionResponse/QueryEvidence reais.
export const result: QuestionResponse = {
  status: 'resultado', resposta: 'Aventura reúne 12 filmes e Drama reúne 8 filmes nesta amostra sintética.',
  avisos: ['A evidência está truncada; o conjunto completo pode conter outras linhas.'],
  consultas: [
    { sql: 'SELECT genero, COUNT(*) AS total FROM dim_genres GROUP BY genero', parametros: {},
      colunas: ['genero', 'total', 'observacao'], linhas: [['Aventura', 12, null], ['Drama', 8, '']], truncado: true },
    { sql: 'SELECT titulo, receita_usd FROM fact_movies_performance WHERE receita_usd > :minimo',
      parametros: { minimo: 0, moeda: null }, colunas: ['titulo', 'receita_usd'],
      linhas: [['Um filme, "especial"\nParte 2', 1500000.25], ['=HYPERLINK("url")', -3.5]], truncado: false },
  ], modelo: 'openai/gpt-oss-120b',
  uso: { chamadas: 2, tokens_entrada: 6500, tokens_saida: 105, tentativas_sql: 2 },
}

export const clarification: QuestionResponse = {
  status: 'esclarecimento', resposta: 'Qual ano ou identificador do filme Home você deseja consultar?',
  avisos: [], consultas: [], modelo: 'openai/gpt-oss-120b',
  uso: { chamadas: 1, tokens_entrada: null, tokens_saida: null, tentativas_sql: 0 },
}
export const empty: QuestionResponse = {
  ...clarification, status: 'sem_dados', resposta: 'Não foram encontrados filmes com esse critério.',
  consultas: [{ sql: 'SELECT titulo FROM dim_movies WHERE titulo = :titulo', parametros: { titulo: 'Inexistente' },
    colunas: ['titulo'], linhas: [], truncado: false }],
}
export const refusal: QuestionResponse = {
  ...clarification, status: 'recusa', resposta: 'A operação solicitada não é permitida no banco somente leitura.',
}
