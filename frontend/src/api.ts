import type { Answer } from './types'

const messages: Record<string, string> = {
  entrada_invalida: 'Revise sua pergunta. Use de 1 a 2.000 caracteres.',
  banco_indisponivel: 'O catálogo está indisponível. Tente novamente mais tarde.',
  configuracao_invalida: 'O serviço precisa ser configurado. Tente novamente quando estiver disponível.',
  modelo_indisponivel: 'O serviço de respostas está indisponível. Tente novamente mais tarde.',
  cota_excedida: 'O limite de consultas do serviço foi atingido. Aguarde antes de tentar novamente.',
  resposta_invalida: 'Não foi possível interpretar a resposta. Tente novamente ou reformule a pergunta.',
  prazo_excedido: 'A consulta demorou mais que o limite. Tente uma pergunta com um recorte menor.',
  conexao_indisponivel: 'Não foi possível conectar ao serviço. Confira a conexão e tente novamente.',
  servico_indisponivel: 'Não foi possível concluir a consulta. Tente novamente mais tarde.',
}
export class ApiError extends Error {
  constructor(public codigo: string) { super(messages[codigo] ?? messages.servico_indisponivel); this.name = 'ApiError' }
}
export function normalizeQuestion(raw: string): string {
  const value = raw.trim()
  if (!value || Array.from(value).length > 2000) throw new ApiError('entrada_invalida')
  return value
}
const record = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value)
const scalar = (value: unknown) => value === null || typeof value === 'string' || (typeof value === 'number' && Number.isFinite(value))
function validAnswer(value: unknown): value is Answer {
  if (!record(value) || typeof value.status !== 'string' || !['resultado', 'esclarecimento', 'recusa', 'sem_dados'].includes(value.status)) return false
  if (typeof value.resposta !== 'string' || !value.resposta.trim() || typeof value.modelo !== 'string') return false
  if (!Array.isArray(value.avisos) || !value.avisos.every(x => typeof x === 'string')) return false
  if (!record(value.uso) || !Object.values(value.uso).every(x => x === null || (typeof x === 'number' && Number.isInteger(x) && x >= 0))) return false
  return Array.isArray(value.consultas) && value.consultas.every(query => {
    if (!record(query) || typeof query.sql !== 'string' || typeof query.truncado !== 'boolean' || !record(query.parametros)) return false
    if (!Object.values(query.parametros).every(scalar) || !Array.isArray(query.colunas) || !query.colunas.every(x => typeof x === 'string')) return false
    const columns = query.colunas.length
    return Array.isArray(query.linhas) && query.linhas.every(row => Array.isArray(row) && row.length === columns && row.every(scalar))
  })
}
export async function askQuestion(pergunta: string): Promise<Answer> {
  const normalized = normalizeQuestion(pergunta)
  let response: Response
  try {
    response = await fetch('/api/perguntas', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pergunta: normalized }) })
  } catch { throw new ApiError('conexao_indisponivel') }
  let body: unknown
  try { body = await response.json() } catch { throw new ApiError(response.ok ? 'resposta_invalida' : 'servico_indisponivel') }
  if (!response.ok) {
    const fallback = ({ 422: 'entrada_invalida', 502: 'resposta_invalida', 503: 'servico_indisponivel', 504: 'prazo_excedido' } as Record<number, string>)[response.status] ?? 'servico_indisponivel'
    const code = record(body) && record(body.detail) && typeof body.detail.codigo === 'string' ? body.detail.codigo : fallback
    throw new ApiError(Object.hasOwn(messages, code) ? code : fallback)
  }
  if (!validAnswer(body)) throw new ApiError('resposta_invalida')
  return body
}
