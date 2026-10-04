import type { Answer, Evidence } from './types'

export function getFilmColumns(evidence: Evidence): { title: number; year: number; poster: number; id: number } | null {
  const columns = evidence.colunas.map(column => column.trim().toLowerCase())
  const find = (aliases: string[]) => columns.findIndex(column => aliases.includes(column))
  const title = find(['titulo', 'titulo_filme', 'filme'])
  const year = find(['ano_lancamento', 'ano'])
  const poster = find(['url_poster', 'poster'])
  const id = find(['sk_movie_id', 'id_filme'])
  if (title < 0 || (year < 0 && poster < 0 && id < 0) || !evidence.linhas.length) return null
  if (evidence.linhas.some(row => typeof row[title] !== 'string' || !String(row[title]).trim())) return null
  return { title, year, poster, id }
}

export function resultTitle(answer: Answer): string {
  if (answer.status !== 'resultado') return { esclarecimento: 'Esclarecimento', sem_dados: 'Sem dados', recusa: 'Recusa' }[answer.status]
  if (answer.consultas.length === 1 && getFilmColumns(answer.consultas[0])) {
    const columns = answer.consultas[0].colunas.map(column => column.trim().toLowerCase())
    if (columns.some(column => /^(receita|bilheteria)_(usd|brl)$/.test(column))) return 'Bilheteria em foco'
    if (columns.includes('popularidade')) return 'Popularidade em foco'
  }
  return 'Uma nova perspectiva'
}
