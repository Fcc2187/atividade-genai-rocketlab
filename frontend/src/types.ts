export type SQLValue = string | number | null
export type Evidence = {
  sql: string
  parametros: Record<string, SQLValue>
  colunas: string[]
  linhas: SQLValue[][]
  truncado: boolean
}
export type Answer = {
  status: 'resultado' | 'esclarecimento' | 'recusa' | 'sem_dados'
  resposta: string
  avisos: string[]
  consultas: Evidence[]
  modelo: string
  uso: Record<string, number | null>
}
export type HistoryEntry = { id: string; pergunta: string; answer: Answer }
