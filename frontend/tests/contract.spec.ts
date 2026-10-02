import { test, expect } from '@playwright/test'
import { askQuestion, checkHealth, ApiError } from '../src/api'
import { toCsv } from '../src/csv'
import { result, clarification } from './fixtures'

const originalFetch = globalThis.fetch
test.afterEach(() => { globalThis.fetch = originalFetch })

test('envia apenas pergunta aparada e mantém as evidências separadas', async () => {
  const requests: Array<[string, RequestInit | undefined]> = []
  globalThis.fetch = async (url, init) => {
    requests.push([String(url), init])
    return Response.json(result)
  }
  expect(await askQuestion('  Filmes por gênero?  ')).toEqual(result)
  expect(requests).toHaveLength(1)
  expect(requests[0][0]).toBe('/api/perguntas')
  expect(requests[0][1]?.method).toBe('POST')
  expect(JSON.parse(String(requests[0][1]?.body))).toEqual({ pergunta: 'Filmes por gênero?' })
})

test('limite usa caracteres Unicode e rejeita vazio e excesso antes do envio', async () => {
  let calls = 0
  globalThis.fetch = async () => { calls++; return Response.json(clarification) }
  await expect(askQuestion('😀'.repeat(2000))).resolves.toEqual(clarification)
  for (const value of ['  \n ', 'a'.repeat(2001), '😀'.repeat(2001)]) {
    await expect(askQuestion(value)).rejects.toMatchObject({ code: 'entrada_invalida' })
  }
  expect(calls).toBe(1)
})

for (const [status, code] of [
  [503, 'banco_indisponivel'], [503, 'configuracao_invalida'], [503, 'modelo_indisponivel'],
  [503, 'cota_excedida'], [502, 'resposta_invalida'], [504, 'prazo_excedido'],
] as const) {
  test(`erro ${code} informa recuperação sem repetir chamada`, async () => {
    let calls = 0
    globalThis.fetch = async () => { calls++; return Response.json({ detail: { codigo: code, mensagem: 'Detalhe interno não exibido' } }, { status }) }
    await expect(askQuestion('Teste')).rejects.toMatchObject({ code })
    expect(calls).toBe(1)
  })
}

test('422 e erros não JSON são compreensíveis e não refletem corpo bruto', async () => {
  globalThis.fetch = async () => Response.json({ detail: [{ loc: ['body', 'pergunta'], msg: 'internal', type: 'too_long' }] }, { status: 422 })
  await expect(askQuestion('Teste')).rejects.toMatchObject({ code: 'entrada_invalida' })
  globalThis.fetch = async () => new Response('<html>segredo</html>', { status: 502 })
  await expect(askQuestion('Teste')).rejects.toThrow(ApiError)
  await expect(askQuestion('Teste')).rejects.not.toThrow('segredo')
})

test('rede e saída fora do contrato não são tratadas como resultado', async () => {
  globalThis.fetch = async () => { throw new TypeError('Failed to fetch') }
  await expect(askQuestion('Teste')).rejects.toMatchObject({ code: 'falha_rede' })
  for (const bad of [{ ...result, avisos: undefined }, { ...result, status: 'ok' }, { ...result, status: ['resultado'] },
    { ...result, consultas: [{ ...result.consultas[0], linhas: [[true, 1, null]] }] }]) {
    globalThis.fetch = async () => Response.json(bad)
    await expect(askQuestion('Teste')).rejects.toMatchObject({ code: 'resposta_invalida' })
  }
})

test('health valida somente contrato do banco', async () => {
  let path = ''
  globalThis.fetch = async (url) => { path = String(url); return Response.json({ status: 'ok', banco: 'disponivel' }) }
  await expect(checkHealth()).resolves.toBeUndefined()
  expect(path).toBe('/api/health')
  globalThis.fetch = async () => Response.json({ status: 'ok' })
  await expect(checkHealth()).rejects.toThrow(ApiError)
})

test('cancelamento mantém AbortError e passa signal ao fetch sem retry', async () => {
  const controller = new AbortController()
  let calls = 0
  globalThis.fetch = async (_url, init) => {
    calls++
    expect(init?.signal).toBe(controller.signal)
    throw new DOMException('Aborted', 'AbortError')
  }
  await expect(askQuestion('Teste', controller.signal)).rejects.toMatchObject({ name: 'AbortError' })
  expect(calls).toBe(1)
})

test('CSV escapa aspas quebra vírgula Unicode e preserva números/null', () => {
  expect(toCsv({ sql: '', parametros: {}, truncado: false, colunas: ['título', 'valor'],
    linhas: [['A, "B"\nC', -3.5], [null, 0]] }))
    .toBe('\ufeff"título","valor"\r\n"A, ""B""\nC","-3.5"\r\n"","0"\r\n')
})

test('CSV neutraliza fórmulas textuais inclusive cabeçalhos sem alterar número negativo', () => {
  expect(toCsv({ sql: '', parametros: {}, truncado: false, colunas: ['=coluna'],
    linhas: [['=SUM(1)'], [' +1'], ['-texto'], ['@comando'], ['\tformula'], [-2]] }))
    .toBe('\ufeff"\'=coluna"\r\n"\'=SUM(1)"\r\n"\' +1"\r\n"\'-texto"\r\n"\'@comando"\r\n"\'\tformula"\r\n"-2"\r\n')
})

test('CSV protege TAB e CR após espaços iniciais conforme o plano', () => {
  expect(toCsv({ sql: '', parametros: {}, truncado: false, colunas: ['texto'],
    linhas: [[' \ttexto'], [' \rtexto'], [' texto comum']] }))
    .toBe('\ufeff"texto"\r\n"\' \ttexto"\r\n"\' \rtexto"\r\n" texto comum"\r\n')
})
