import { test, expect } from '@playwright/test'
import { rankingAnswer, statusAnswers } from './fixtures'

test('formata unidades explícitas sem presumir moeda ou perder valores originais', async () => {
  const { formatValue, columnLabel } = await import('../src/valueFormatting')
  for (const [value, column, expected] of [
    [1234.5, 'receita_usd', 'US$ 1.234,50'], [1234.5, 'receita_brl', 'R$ 1.234,50'],
    [60, 'margem_percentual', '60%'], [60.12345, 'margem_media_percentual', '60,12%'],
    [2009, 'ano_lancamento', '2009'], [2009, 'id_filme', '2009'],
    [0, 'filmes_validos', '0'], [null, 'receita_usd', 'Não informado'], ['', 'titulo', 'Texto vazio'],
    [7.123456, 'nota_imdb', '7,12'], [1000.123456789, 'misterio', '1.000,123456789'],
    [42, 'receita_sem_unidade', '42'], [42, 'bilheteria_brl', 'R$ 42,00'],
  ] as const) expect(formatValue(value, column).replaceAll('\u00a0', ' ')).toBe(expected)
  expect(columnLabel('receita_usd')).toBe('Receita (USD)')
  expect(columnLabel('margem_media_percentual')).toBe('Margem média (%)')
  expect(columnLabel('coluna_desconhecida')).toBe('coluna desconhecida')
})

test.describe('contrato da consulta', () => {
  test('valida trim e pontos de código Unicode nos limites', async () => {
    const { normalizeQuestion } = await import('../src/api')
    expect(normalizeQuestion('  Avatar  ')).toBe('Avatar')
    expect(normalizeQuestion('🎬'.repeat(2000))).toBe('🎬'.repeat(2000))
    expect(() => normalizeQuestion('🎬'.repeat(2001))).toThrow()
    expect(() => normalizeQuestion(' \n ')).toThrow()
  })

  test('envia somente a pergunta normalizada e aceita os quatro status', async () => {
    const { askQuestion } = await import('../src/api')
    const original = globalThis.fetch
    try {
      for (const answer of Object.values(statusAnswers)) {
        globalThis.fetch = async (url, options) => {
          expect(url).toBe('/api/perguntas')
          expect(options?.method).toBe('POST')
          expect(JSON.parse(options?.body as string)).toEqual({ pergunta: 'Avatar' })
          return new Response(JSON.stringify(answer))
        }
        expect(await askQuestion(' Avatar ')).toEqual(answer)
      }
    } finally { globalThis.fetch = original }
  })

  test('recusa corpo incompatível, JSON malformado e falha de rede', async () => {
    const { askQuestion } = await import('../src/api')
    const original = globalThis.fetch
    const bodies = ['{broken', '{}', JSON.stringify({ ...rankingAnswer, status: 'unexpected' }), JSON.stringify({ ...rankingAnswer, consultas: [{ ...rankingAnswer.consultas[0], linhas: [[42]] }] })]
    try {
      for (const body of bodies) {
        globalThis.fetch = async () => new Response(body)
        await expect(askQuestion('Avatar')).rejects.toMatchObject({ codigo: 'resposta_invalida' })
      }
      globalThis.fetch = async () => { throw new TypeError('private network details') }
      await expect(askQuestion('Avatar')).rejects.toMatchObject({ codigo: 'conexao_indisponivel' })
    } finally { globalThis.fetch = original }
  })

  test('recusa status que só coincide após coerção de tipo', async () => {
    const { askQuestion } = await import('../src/api')
    const original = globalThis.fetch
    try {
      globalThis.fetch = async () => new Response(JSON.stringify({ ...rankingAnswer, status: ['resultado'] }))
      await expect(askQuestion('Avatar')).rejects.toMatchObject({ codigo: 'resposta_invalida' })
    } finally { globalThis.fetch = original }
  })
})

test.describe('exportacao e copia', () => {
  test('CSV usa BOM CRLF e não inventa linhas truncadas', async () => {
    const { toCsv } = await import('../src/csv')
    expect(toCsv({ sql: '', parametros: {}, colunas: ['valor'], linhas: [['=1+1'], [-42], [null]], truncado: true })).toBe('\uFEFFvalor\r\n\'=1+1\r\n-42\r\n\r\n')
  })
  test('protege fórmulas e escapa separadores, aspas e quebras', async () => {
    const { toCsv } = await import('../src/csv')
    const e = { sql: '', parametros: {}, colunas: ['texto'], linhas: [['a,b'], ['a"b'], ['a\nb'], ['+cmd'], ['-cmd'], ['@cmd'], ['\t=1'], ['\r=1'], ['  =1'], ['']], truncado: false }
    expect(toCsv(e)).toBe('\uFEFFtexto\r\n"a,b"\r\n"a""b"\r\n"a\nb"\r\n\'+cmd\r\n\'-cmd\r\n\'@cmd\r\n\'\t=1\r\n"\'\r=1"\r\n\'  =1\r\n\r\n')
  })
})
