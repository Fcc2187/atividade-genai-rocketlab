export type SqlValue = string | number | null
export interface QueryEvidence {
  sql: string
  parametros: Record<string, SqlValue>
  colunas: string[]
  linhas: SqlValue[][]
  truncado: boolean
}
export type AnswerStatus = 'resultado' | 'esclarecimento' | 'sem_dados' | 'recusa'
export interface QuestionResponse {
  status: AnswerStatus
  resposta: string
  avisos: string[]
  consultas: QueryEvidence[]
  modelo: string
  uso: Record<string, number | null>
}

export interface HistoryEntry {
  id: string
  pergunta: string
  createdAt: number
  duration: number
  response?: QuestionResponse
  error?: { code: string; message: string }
}
