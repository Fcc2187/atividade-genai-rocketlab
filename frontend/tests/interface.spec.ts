import { test, expect, type Page } from '@playwright/test'
import { result, clarification, empty, refusal } from './fixtures'

test.beforeEach(async ({ page }) => {
  await page.route('**/api/health', route => route.fulfill({ json: { status: 'ok', banco: 'disponivel' } }))
})
const field = (page: Page) => page.getByRole('textbox', { name: 'Sua pergunta' })
const send = (page: Page) => page.getByRole('button', { name: 'Consultar catálogo', exact: true })
async function submit(page: Page, text = 'Quantos filmes existem por gênero?') {
  await field(page).fill(text)
  await send(page).click()
}
async function history(page: Page) {
  const toggle = page.getByRole('button', { name: 'Histórico', exact: true })
  if (await toggle.isVisible() && await toggle.getAttribute('aria-expanded') === 'false') await toggle.click()
}

test('entrada inicial tem cinco categorias e exemplo só preenche o campo', async ({ page }) => {
  let calls = 0
  await page.route('**/api/perguntas', route => { calls++; return route.fulfill({ json: result }) })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'O que você quer descobrir?' })).toBeVisible()
  for (const category of ['Finanças', 'Popularidade', 'Elenco e equipe', 'Gêneros e produtoras', 'Avaliações']) {
    await expect(page.getByRole('button', { name: category, exact: true })).toBeVisible()
  }
  await page.getByRole('button', { name: 'Finanças', exact: true }).click()
  await page.getByRole('button', { name: 'Top 10 filmes com maior receita em R$', exact: true }).click()
  await expect(field(page)).toHaveValue('Top 10 filmes com maior receita em R$')
  expect(calls).toBe(0)
  await expect(field(page)).toBeFocused()
  await page.screenshot({ path: `test-results/${test.info().project.name}-initial.png`, fullPage: true })
})

test('validação impede vazio/excesso sem gastar consulta e mantém Unicode', async ({ page }) => {
  let calls = 0
  await page.route('**/api/perguntas', route => { calls++; return route.fulfill({ json: clarification }) })
  await page.goto('/')
  await field(page).fill('  ')
  await send(page).click()
  await expect(page.getByRole('alert')).toContainText('Escreva')
  await expect(field(page)).toBeFocused()
  await field(page).fill('😀'.repeat(2001))
  await send(page).click()
  await expect(page.getByRole('alert')).toContainText('2000')
  expect(calls).toBe(0)
  await field(page).fill('😀'.repeat(2000))
  await send(page).click()
  await expect(page.getByRole('heading', { name: 'Precisamos de um detalhe' })).toBeVisible()
  expect(calls).toBe(1)
})

test('loading tem tempo decorrido e bloqueia duplicação sem progresso inventado', async ({ page }) => {
  let calls = 0
  let finish!: () => void
  const wait = new Promise<void>(resolve => { finish = resolve })
  await page.route('**/api/perguntas', async route => { calls++; await wait; await route.fulfill({ json: result }) })
  await page.goto('/')
  await submit(page)
  await expect(page.getByRole('status').filter({ hasText: 'Consultando o catálogo' })).toBeVisible()
  await expect(page.getByLabel('Tempo decorrido')).toContainText(/00:0[1-9]/)
  await expect(page.getByRole('button', { name: 'Consultando…' })).toBeDisabled()
  await expect(field(page)).toBeDisabled()
  await expect(page.getByRole('progressbar')).toHaveCount(0)
  expect(calls).toBe(1)
  finish()
  await expect(page.getByRole('heading', { name: 'Resultado da consulta' })).toBeVisible()
})

test('mostra avisos duas tabelas truncamento e detalhes de cada evidência', async ({ page }) => {
  await page.route('**/api/perguntas', route => route.fulfill({ json: result }))
  await page.goto('/')
  await submit(page)
  await expect(page.getByText(result.resposta, { exact: true })).toBeVisible()
  await expect(page.getByText(result.avisos[0], { exact: true })).toBeVisible()
  await expect(page.getByRole('table')).toHaveCount(2)
  await expect(page.getByText('Dados parciais', { exact: true })).toBeVisible()
  await expect(page.getByRole('cell', { name: 'Sem valor', exact: true })).toBeVisible()
  await expect(page.getByRole('cell', { name: 'Texto vazio', exact: true })).toBeVisible()
  await page.getByText('SQL e parâmetros da consulta 2', { exact: true }).click()
  await expect(page.getByText(result.consultas[1].sql, { exact: true })).toBeVisible()
  await page.getByText('Detalhes do modelo e uso', { exact: true }).click()
  await expect(page.getByText('openai/gpt-oss-120b', { exact: true })).toBeVisible()
  await expect(page.getByText('6500', { exact: true })).toBeVisible()
  await page.screenshot({ path: `test-results/${test.info().project.name}-result.png`, fullPage: true })
})

test('exporta evidência própria em CSV e copia resposta sem nova consulta', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  let calls = 0
  await page.route('**/api/perguntas', route => { calls++; return route.fulfill({ json: result }) })
  await page.goto('/')
  await submit(page)
  await page.getByRole('button', { name: 'Copiar resposta', exact: true }).click()
  await expect(page.getByRole('status').filter({ hasText: 'Resposta copiada' })).toBeVisible()
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(result.resposta)
  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Exportar consulta 2 em CSV' }).click()
  const file = await download
  expect(file.suggestedFilename()).toBe('cinedata-consulta-2.csv')
  const stream = await file.createReadStream()
  const chunks: Buffer[] = []
  for await (const chunk of stream!) chunks.push(chunk)
  const csv = Buffer.concat(chunks).toString('utf8')
  expect(csv).toContain('"titulo","receita_usd"')
  expect(csv).toContain('"Um filme, ""especial""\nParte 2","1500000.25"')
  expect(csv).not.toContain('genero')
  expect(calls).toBe(1)
})

for (const [fixture, title] of [[clarification, 'Precisamos de um detalhe'], [empty, 'Nenhum dado encontrado'], [refusal, 'Consulta não permitida']] as const) {
  test(`representa ${fixture.status} e valores de uso ausentes`, async ({ page }) => {
    await page.route('**/api/perguntas', route => route.fulfill({ json: fixture }))
    await page.goto('/')
    await submit(page)
    await expect(page.getByRole('heading', { name: title })).toBeVisible()
    await expect(page.getByText(fixture.resposta, { exact: true })).toBeVisible()
    if (fixture.status === 'sem_dados') await expect(page.getByText('Esta consulta não retornou linhas.')).toBeVisible()
    await page.getByText('Detalhes do modelo e uso', { exact: true }).click()
    await expect(page.getByText('Não informado', { exact: true })).toHaveCount(2)
  })
}

test('esclarecimento permite editar e envia pergunta independente', async ({ page }) => {
  const bodies: unknown[] = []
  await page.route('**/api/perguntas', route => {
    bodies.push(route.request().postDataJSON())
    return route.fulfill({ json: bodies.length === 1 ? clarification : result })
  })
  await page.goto('/')
  await submit(page, 'Qual a nota de Home?')
  await page.getByRole('button', { name: 'Editar pergunta', exact: true }).click()
  await expect(field(page)).toBeFocused()
  await expect(field(page)).toHaveValue('Qual a nota de Home?')
  await submit(page, 'Qual a nota IMDb de Home de 2015?')
  await expect(page.getByRole('heading', { name: 'Resultado da consulta' })).toBeVisible()
  expect(bodies).toEqual([{ pergunta: 'Qual a nota de Home?' }, { pergunta: 'Qual a nota IMDb de Home de 2015?' }])
  await history(page)
  await page.getByRole('button', { name: /Revisitar: Qual a nota de Home\?$/ }).click()
  await expect(page.getByRole('heading', { name: 'Precisamos de um detalhe' })).toBeVisible()
  expect(bodies).toHaveLength(2)
})

test('histórico em memória revisita resultado e nova consulta não chama API', async ({ page }) => {
  let calls = 0
  await page.route('**/api/perguntas', route => { calls++; return route.fulfill({ json: result }) })
  await page.goto('/')
  await submit(page, 'Filmes por gênero')
  await expect(page.getByRole('heading', { name: 'Resultado da consulta' })).toBeVisible()
  await history(page)
  await page.getByRole('button', { name: 'Nova consulta', exact: true }).click()
  await expect(field(page)).toHaveValue('')
  await history(page)
  await page.getByRole('button', { name: 'Revisitar: Filmes por gênero', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Resultado da consulta' })).toBeVisible()
  expect(calls).toBe(1)
  await page.reload()
  await history(page)
  await expect(page.locator('.history-empty:visible').getByText('Suas consultas aparecerão aqui.')).toBeVisible()
})

for (const [code, status, match] of [
  ['cota_excedida', 503, 'limite'], ['modelo_indisponivel', 503, 'Groq'],
  ['configuracao_invalida', 503, 'configuração'], ['banco_indisponivel', 503, 'banco'],
  ['resposta_invalida', 502, 'resposta'], ['prazo_excedido', 504, 'tempo'], ['entrada_invalida', 422, 'pergunta'],
] as const) {
  test(`erro ${code} mantém texto e permite tentativa somente explícita`, async ({ page }) => {
    let calls = 0
    await page.route('**/api/perguntas', route => { calls++; return route.fulfill({ status, json: { detail: { codigo: code, mensagem: 'Mensagem interna' } } }) })
    await page.goto('/')
    await submit(page, 'Minha pergunta')
    await expect(page.getByRole('alert')).toContainText(new RegExp(match, 'i'))
    await expect(page.getByRole('alert')).not.toContainText('Mensagem interna')
    await expect(field(page)).toHaveValue('Minha pergunta')
    await expect(send(page)).toBeEnabled()
    expect(calls).toBe(1)
  })
}

test('falha de rede preserva pergunta e não confunde health com Groq', async ({ page }) => {
  await page.route('**/api/perguntas', route => route.abort())
  await page.goto('/')
  await expect(page.getByText('Banco disponível', { exact: true })).toBeVisible()
  await expect(page.getByText(/não verifica o Groq/)).toBeVisible()
  await submit(page, 'Pergunta offline')
  await expect(page.getByRole('alert')).toContainText('conectar')
  await expect(field(page)).toHaveValue('Pergunta offline')
})

test('mobile tabela rola internamente e layout não ultrapassa viewport', async ({ page }) => {
  const wide = { ...result, consultas: [{ ...result.consultas[0], colunas: ['Título muito extenso', 'Coluna B', 'Coluna C', 'Coluna D', 'Coluna E'],
    linhas: [['Um título com muitas palavras para conferir a leitura em uma tabela', 1, 2, 3, 4]] }] }
  await page.route('**/api/perguntas', route => route.fulfill({ json: wide }))
  await page.goto('/')
  await submit(page)
  await expect(page.getByRole('table')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  const container = page.getByRole('region', { name: 'Tabela da consulta 1' })
  await expect(container).toHaveAttribute('tabindex', '0')
  if (test.info().project.name === 'mobile') {
    expect(await container.evaluate(el => el.scrollWidth > el.clientWidth)).toBe(true)
    await container.evaluate(el => { el.scrollLeft = 200 })
    expect(await container.evaluate(el => el.scrollLeft)).toBeGreaterThan(0)
  }
})

test('movimento pode pausar e reduced-motion mantém formas estáticas', async ({ page }) => {
  await page.goto('/')
  const shape = page.locator('.ambient-shape').first()
  await expect(shape).toHaveCSS('animation-play-state', 'running')
  await history(page)
  await page.getByRole('button', { name: 'Pausar animação' }).click()
  await expect(shape).toHaveCSS('animation-play-state', 'paused')
  await page.getByRole('button', { name: 'Retomar animação' }).click()
  await expect(shape).toHaveCSS('animation-play-state', 'running')
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await expect(shape).toHaveCSS('animation-name', 'none')
  await expect(page.locator('.ambient')).toHaveCSS('pointer-events', 'none')
})

test('resultado troca apresentação inicial por leitura e composer abaixo das evidências', async ({ page }) => {
  await page.route('**/api/perguntas', route => route.fulfill({ json: result }))
  await page.goto('/')
  await submit(page)
  await expect(page.getByRole('heading', { name: 'O que você quer descobrir?' })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Explore o catálogo', exact: true })).toBeVisible()
  const table = await page.getByRole('table').last().boundingBox()
  const composer = await field(page).boundingBox()
  expect(composer!.y).toBeGreaterThan(table!.y + table!.height)
  if (test.info().project.name === 'desktop') await expect(page.getByRole('complementary', { name: 'Explorar o catálogo' })).toBeVisible()
})

test('histórico mobile é modal e Escape restaura foco ao botão de abertura', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  const trigger = page.getByRole('button', { name: 'Histórico', exact: true })
  await trigger.click()
  await expect(page.getByRole('dialog', { name: 'Histórico da sessão' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Fechar histórico', exact: true })).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(trigger).toBeFocused()
})

test('teclado acessa exemplos campo envio e detalhes sem perda de foco', async ({ page }) => {
  await page.route('**/api/perguntas', route => route.fulfill({ json: result }))
  await page.goto('/')
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Ir para a consulta' })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('main')).toBeFocused()
  await field(page).focus()
  await field(page).fill('Consulta com teclado')
  await page.keyboard.press('Control+Enter')
  await expect(page.getByRole('heading', { name: 'Resultado da consulta' })).toBeVisible()
  await page.getByText('Detalhes do modelo e uso', { exact: true }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText('openai/gpt-oss-120b', { exact: true })).toBeVisible()
})

test('atalho de pular fica oculto durante leitura e surge somente com foco', async ({ page }) => {
  await page.goto('/')
  const skip = page.getByRole('link', { name: 'Ir para a consulta' })
  await expect(skip).toHaveCSS('clip-path', 'inset(50%)')
  await page.keyboard.press('Tab')
  await expect(skip).toBeFocused()
  await expect(skip).toHaveCSS('clip-path', 'none')
})

test('histórico preserva erros e permanece bloqueado durante consulta pendente', async ({ page }) => {
  let calls = 0
  let finish!: () => void
  const pending = new Promise<void>(resolve => { finish = resolve })
  await page.route('**/api/perguntas', async route => {
    calls++
    if (calls === 1) await route.fulfill({ status: 503, json: { detail: { codigo: 'cota_excedida', mensagem: 'limite' } } })
    else { await pending; await route.fulfill({ json: result }) }
  })
  await page.goto('/')
  await submit(page, 'Minha primeira consulta')
  await expect(page.getByRole('alert')).toContainText('limite')
  await submit(page, 'Minha segunda consulta')
  await history(page)
  await expect(page.getByRole('button', { name: 'Revisitar: Minha primeira consulta' })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Nova consulta', exact: true })).toBeDisabled()
  finish()
  await expect(page.getByRole('heading', { name: 'Resultado da consulta' })).toBeVisible()
  await history(page)
  await page.getByRole('button', { name: 'Revisitar: Minha primeira consulta' }).click()
  await expect(page.getByRole('alert')).toContainText('limite')
  expect(calls).toBe(2)
})

test('conteúdo longo permanece legível em tela estreita tablet e desktop', async ({ page }) => {
  const long = { ...result, resposta: 'Texto de análise com evidência. '.repeat(120), avisos: ['Ressalva '.repeat(50)],
    consultas: [{ ...result.consultas[1], sql: 'SELECT ' + 'coluna'.repeat(1000), linhas: [['Título '.repeat(200), 1]] }] }
  await page.route('**/api/perguntas', route => route.fulfill({ json: long }))
  await page.goto('/')
  await submit(page)
  await expect(page.getByRole('heading', { name: 'Resultado da consulta' })).toBeVisible()
  await page.getByText('SQL e parâmetros da consulta 1', { exact: true }).click()
  for (const width of [320, 800, 1920]) {
    await page.setViewportSize({ width, height: 900 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await expect(page.getByText(long.resposta, { exact: true })).toBeVisible()
  }
})

test('falha de copiar tem recuperação acessível sem alterar resposta', async ({ page }) => {
  await page.addInitScript(() => Object.defineProperty(navigator, 'clipboard', { value: { writeText: async () => { throw new DOMException('Permission denied') } } }))
  await page.route('**/api/perguntas', route => route.fulfill({ json: result }))
  await page.goto('/')
  await submit(page)
  await page.getByRole('button', { name: 'Copiar resposta', exact: true }).click()
  await expect(page.getByRole('status').filter({ hasText: 'copie manualmente' })).toBeVisible()
  await expect(page.getByText(result.resposta, { exact: true })).toBeVisible()
})

test('Enter edita, IME não envia e dois submits no mesmo ciclo geram um POST', async ({ page }) => {
  let calls = 0
  await page.route('**/api/perguntas', route => { calls++; return route.fulfill({ json: result }) })
  await page.goto('/')
  await field(page).fill('Linha um')
  await field(page).press('Enter')
  await expect(field(page)).toHaveValue('Linha um\n')
  await field(page).dispatchEvent('keydown', { key: 'Enter', ctrlKey: true, isComposing: true })
  expect(calls).toBe(0)
  await page.locator('form').evaluate(form => {
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
  })
  await expect(page.getByRole('heading', { name: 'Resultado da consulta' })).toBeVisible()
  expect(calls).toBe(1)
})

test('mobile inicial deixa envio visível e drawer contém o foco', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(send(page)).toBeInViewport()
  await page.getByRole('button', { name: 'Histórico', exact: true }).click()
  await page.getByRole('button', { name: 'Pausar animação' }).focus()
  await page.keyboard.press('Tab')
  // O Chromium pode passar pelos controles do navegador entre o último e o primeiro item.
  await expect(field(page)).not.toBeFocused()
  await page.keyboard.press('Tab')
  expect(await page.evaluate(() => !!document.activeElement?.closest('dialog'))).toBe(true)
  await page.keyboard.press('Escape')
  await expect(field(page)).toHaveCSS('font-size', '16px')
})
