import type { QuestionResponse, QueryEvidence } from './types'

const messages: Record<string, string> = {
  entrada_invalida: 'Confira a pergunta: escreva entre 1 e 2000 caracteres e envie novamente.',
  banco_indisponivel: 'O banco de filmes não está disponível. Confira se o arquivo está na pasta do backend.',
  configuracao_invalida: 'A configuração do backend precisa ser revisada. Confira o arquivo .env no servidor.',
  modelo_indisponivel: 'O Groq não está disponível agora. Confira a conexão e a configuração do backend antes de tentar novamente.',
  cota_excedida: 'O limite de uso do Groq foi atingido. Aguarde a renovação da cota antes de enviar outra consulta.',
  resposta_invalida: 'Não foi possível validar a resposta. Você pode reformular a pergunta e enviá-la novamente.',
  prazo_excedido: 'A consulta ultrapassou o tempo disponível. Experimente uma pergunta mais específica.',
  falha_rede: 'Não foi possível conectar ao backend. Confira se ele está em execução e se há conexão de rede.',
  erro_servidor: 'O servidor não conseguiu concluir a consulta. Confira o backend antes de tentar novamente.',
}

export class ApiError extends Error {
  constructor(public code: string, message = messages[code] ?? messages.erro_servidor, public httpStatus?: number) {
    super(message)
    this.name = 'ApiError'
  }
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
function scalar(value: unknown): boolean {
  return value === null || typeof value === 'string' || typeof value === 'number' && Number.isFinite(value)
}
function evidence(value: unknown): value is QueryEvidence {
  return record(value) && typeof value.sql === 'string' && record(value.parametros)
    && Object.values(value.parametros).every(scalar) && typeof value.truncado === 'boolean'
    && Array.isArray(value.colunas) && value.colunas.length <= 64 && value.colunas.every(col => typeof col === 'string')
    && Array.isArray(value.linhas) && value.linhas.length <= 100
    && value.linhas.every(row => Array.isArray(row) && row.length === (value.colunas as unknown[]).length && row.every(scalar))
}
function answer(value: unknown): value is QuestionResponse {
  return record(value) && typeof value.status === 'string' && ['resultado', 'esclarecimento', 'sem_dados', 'recusa'].includes(value.status)
    && typeof value.resposta === 'string' && value.resposta.trim().length > 0
    && Array.isArray(value.avisos) && value.avisos.every(warning => typeof warning === 'string')
    && Array.isArray(value.consultas) && value.consultas.every(evidence)
    && typeof value.modelo === 'string' && record(value.uso)
    && Object.values(value.uso).every(item => item === null || typeof item === 'number' && Number.isInteger(item) && item >= 0)
}

async function request(path: string, init?: RequestInit): Promise<unknown> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, { ...init, cache: 'no-store' })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError('falha_rede')
  }
  let body: unknown
  try { body = await response.json() } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    body = null
  }
  if (!response.ok) {
    const detail = record(body) && record(body.detail) ? body.detail : null
    const code = typeof detail?.codigo === 'string' && Object.hasOwn(messages, detail.codigo) ? detail.codigo
      : response.status === 422 ? 'entrada_invalida'
      : response.status === 504 ? 'prazo_excedido'
      : response.status === 502 ? 'resposta_invalida' : 'erro_servidor'
    throw new ApiError(code, undefined, response.status)
  }
  return body
}

export async function askQuestion(pergunta: string, signal?: AbortSignal): Promise<QuestionResponse> {
  const trimmed = pergunta.trim()
  if (!trimmed || Array.from(trimmed).length > 2000) throw new ApiError('entrada_invalida')
  const body = await request('/perguntas', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pergunta: trimmed }), signal,
  })
  if (!answer(body)) throw new ApiError('resposta_invalida')
  return body
}

export async function checkHealth(signal?: AbortSignal): Promise<void> {
  const body = await request('/health', { signal })
  if (!record(body) || body.status !== 'ok' || body.banco !== 'disponivel') throw new ApiError('banco_indisponivel')
}
