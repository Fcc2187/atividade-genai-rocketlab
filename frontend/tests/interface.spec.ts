import { test, expect } from '@playwright/test'
import { rankingAnswer, aggregateAnswer, longAnswer, statusAnswers } from './fixtures'

test.describe('historico e acessibilidade', () => {
  test('reabre respostas sem POST extra e reload limpa só o histórico', async ({ page }) => {
    let calls = 0
    await page.route('**/api/perguntas', route => { calls++; return route.fulfill({ json: rankingAnswer }) })
    await page.goto('/')
    const input = page.getByRole('textbox', { name: 'Sua pergunta' })
    for (const question of ['Primeira pergunta', 'Segunda pergunta']) {
      await input.fill(question)
      await page.getByRole('button', { name: 'Consultar →' }).click()
      await expect(page.getByText(rankingAnswer.resposta, { exact: true })).toBeVisible()
    }
    const historyButton = page.getByRole('button', { name: 'Histórico', exact: true })
    if (await historyButton.isVisible()) await historyButton.click()
    await page.getByRole('button', { name: 'Primeira pergunta', exact: true }).click()
    await expect(input).toHaveValue('Primeira pergunta')
    expect(calls).toBe(2)
    if (await historyButton.isVisible()) await historyButton.click()
    await page.getByRole('button', { name: '＋ Nova pergunta' }).click()
    await expect(input).toBeFocused()
    await expect(input).toHaveValue('')
    await expect(page.getByText(rankingAnswer.resposta, { exact: true })).toHaveCount(0)
    await page.getByRole('button', { name: 'Ativar modo escuro' }).click()
    await page.reload()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
    if (await historyButton.isVisible()) await historyButton.click()
    await expect(page.getByRole('navigation', { name: 'Histórico da aba' }).getByText('Nenhuma pergunta nesta aba.', { exact: true })).toBeVisible()
  })

  test('drawer contém foco e Escape devolve foco ao acionador', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/')
    const trigger = page.getByRole('button', { name: 'Histórico', exact: true })
    await trigger.click()
    const dialog = page.getByRole('dialog', { name: 'Histórico da aba' })
    await expect(dialog).toBeVisible()
    for (let i = 0; i < 6; i++) {
      await page.keyboard.press('Tab')
      expect(await dialog.evaluate(element => element.contains(document.activeElement))).toBe(true)
    }
    await page.keyboard.press('Escape')
    await expect(dialog).not.toBeVisible()
    await expect(trigger).toBeFocused()
  })

  test('impede nova pergunta durante consulta tardia e mantém tema utilizável', async ({ page }) => {
    let finish!: () => void
    const gate = new Promise<void>(resolve => { finish = resolve })
    await page.route('**/api/perguntas', async route => { await gate; await route.fulfill({ json: rankingAnswer }) })
    await page.goto('/')
    await page.getByRole('textbox', { name: 'Sua pergunta' }).fill('Avatar')
    await page.getByRole('button', { name: 'Consultar →' }).click()
    await expect(page.getByRole('button', { name: 'Consultando…' })).toBeDisabled()
    const trigger = page.getByRole('button', { name: 'Histórico', exact: true })
    if (await trigger.isVisible()) await trigger.click()
    await expect(page.getByRole('button', { name: '＋ Nova pergunta' })).toBeDisabled()
    if (await trigger.isVisible()) await page.keyboard.press('Escape')
    await page.getByRole('button', { name: 'Ativar modo escuro' }).click()
    finish()
    await expect(page.getByText(rankingAnswer.resposta, { exact: true })).toBeVisible()
  })

  test('ajuda tem conteúdo de uso e fecha com retorno de foco', async ({ page }) => {
    await page.goto('/')
    const help = page.getByRole('button', { name: 'Como usar' }).first()
    await help.click()
    const dialog = page.getByRole('dialog', { name: 'Como usar o CineData' })
    await expect(dialog).toBeVisible()
    await expect(dialog).toContainText('Cada pergunta é independente')
    await page.keyboard.press('Escape')
    await expect(help).toBeFocused()
  })

  for (const theme of ['light', 'dark'] as const) test(`320px, texto 200% e espaçamento no tema ${theme}`, async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 812 })
    await page.emulateMedia({ colorScheme: theme, reducedMotion: 'reduce' })
    const wideAnswer = { ...longAnswer, avisos: ['https://example.test/' + 'a'.repeat(200)], modelo: 'modelo-' + 'x'.repeat(200) }
    await page.route('**/api/perguntas', route => route.fulfill({ json: wideAnswer }))
    await page.goto('/')
    await page.getByRole('textbox', { name: 'Sua pergunta' }).fill('Filmes')
    await page.getByRole('button', { name: 'Consultar →' }).click()
    await page.getByText('Ver SQL e dados', { exact: true }).click()
    await page.getByText('Modelo e uso', { exact: true }).click()
    const fontSizes = await page.locator('.answer-text, .film-title > p:first-child').evaluateAll(elements => elements.map(x => parseFloat(getComputedStyle(x).fontSize)))
    await page.addStyleTag({ content: 'html {font-size: 200%} p,li,button,textarea,label,summary,dt,dd,h1,h2,h3,th,td {line-height:1.5 !important; letter-spacing:.12em !important; word-spacing:.16em !important} p {margin-bottom:2em !important}' })
    const enlargedSizes = await page.locator('.answer-text, .film-title > p:first-child').evaluateAll(elements => elements.map(x => parseFloat(getComputedStyle(x).fontSize)))
    expect(enlargedSizes).toEqual(fontSizes.map(size => size * 2))
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await expect(page.getByText(longAnswer.consultas[0].linhas[0][0] as string, { exact: true }).first()).toBeVisible()
    const toggle = page.getByRole('button', { name: theme === 'light' ? 'Ativar modo escuro' : 'Ativar modo claro' })
    await toggle.focus()
    await page.keyboard.press('Enter')
    await expect(page.locator('html')).toHaveAttribute('data-theme', theme === 'light' ? 'dark' : 'light')
    const csv = page.getByRole('button', { name: 'Exportar CSV da consulta 1' })
    await csv.focus()
    await expect(csv).toBeFocused()
  })

  test('aviso e modelo extensos conservam reflow em 320 px', async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 812 })
    const answer = { ...rankingAnswer, avisos: ['https://example.test/' + 'a'.repeat(200)], modelo: 'modelo-' + 'x'.repeat(200) }
    await page.route('**/api/perguntas', route => route.fulfill({ json: answer }))
    await page.goto('/')
    await page.getByRole('textbox', { name: 'Sua pergunta' }).fill('Filmes')
    await page.getByRole('button', { name: 'Consultar →' }).click()
    await page.getByText('Modelo e uso', { exact: true }).click()
    await expect(page.getByText(answer.avisos[0], { exact: true })).toBeVisible()
    await expect(page.getByText('Modelo: ' + answer.modelo, { exact: true })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
})

test.describe('filmes e evidencias', () => {
  test('mantém a métrica legível em mobile com valor completo acessível', async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 812 })
    await page.route('**/api/perguntas', route => route.fulfill({ json: rankingAnswer }))
    await page.goto('/')
    await page.getByRole('textbox', { name: 'Sua pergunta' }).fill('Filmes')
    await page.getByRole('button', { name: 'Consultar →' }).click()
    const metric = page.locator('.film-metrics dd').first()
    await expect(metric.getByText('US$ 2,92 bi', { exact: true })).toBeVisible()
    await expect(metric).toContainText('2.920.000.000,00')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
  test('pôsteres e fallback mantêm identificação e métrica', async ({ page }) => {
    await page.route('**/api/perguntas', route => route.fulfill({ json: rankingAnswer }))
    await page.route('https://images.example.test/**', route => route.fulfill(route.request().url().endsWith('avatar.png') ? { path: 'tests/assets/avatar.png' } : { status: 404 }))
    await page.goto('/')
    await page.getByRole('textbox', { name: 'Sua pergunta' }).fill('Filmes')
    await page.getByRole('button', { name: 'Consultar →' }).click()
    const films = page.getByRole('list', { name: 'Filmes da consulta 1' })
    await expect(films.getByText('Avatar', { exact: true })).toBeVisible()
    await expect(films.getByRole('img', { name: 'Pôster de Avatar', exact: true })).toBeVisible()
    await expect(films.getByText('Pôster indisponível')).toHaveCount(4)
    await expect(films.getByText(/2\.920\.000\.000/)).toBeVisible()
    await page.getByText('Ver SQL e dados', { exact: true }).click()
    await expect(page.getByRole('table')).toBeVisible()
    await page.getByText('SQL e parâmetros', { exact: true }).click()
    await expect(page.locator('pre').first()).toContainText('SELECT titulo')
  })

  test('agregações têm tabela completa sem inventar filmes', async ({ page }) => {
    await page.route('**/api/perguntas', route => route.fulfill({ json: aggregateAnswer }))
    await page.goto('/')
    await page.getByRole('textbox', { name: 'Sua pergunta' }).fill('Gêneros')
    await page.getByRole('button', { name: 'Consultar →' }).click()
    await expect(page.getByRole('list', { name: /Filmes da consulta/ })).toHaveCount(0)
    await page.getByText('Ver SQL e dados', { exact: true }).click()
    const table = page.getByRole('table')
    await expect(table.getByText('Drama', { exact: true })).toBeVisible()
    await expect(table.getByText('Não informado', { exact: true })).toBeVisible()
    await expect(table.getByText('Texto vazio', { exact: true })).toBeVisible()
  })
})

test.describe('exportacao e copia', () => {
  test('exporta cada evidência com truncamento e só os dados recebidos', async ({ page }) => {
    await page.route('**/api/perguntas', route => route.fulfill({ json: { ...aggregateAnswer, consultas: [aggregateAnswer.consultas[0], { ...aggregateAnswer.consultas[0], linhas: [['Drama', 42]], truncado: true }] } }))
    await page.goto('/')
    await page.getByRole('textbox', { name: 'Sua pergunta' }).fill('Gêneros')
    await page.getByRole('button', { name: 'Consultar →' }).click()
    await page.getByText('Ver SQL e dados', { exact: true }).click()
    await expect(page.getByRole('table')).toHaveCount(2)
    const downloaded = page.waitForEvent('download')
    await page.getByRole('button', { name: 'Exportar CSV da consulta 2' }).click()
    const download = await downloaded
    expect(download.suggestedFilename()).toBe('cinedata-consulta-2-truncada.csv')
    const stream = await download.createReadStream()
    const chunks: Buffer[] = []
    for await (const chunk of stream!) chunks.push(Buffer.from(chunk))
    expect(Buffer.concat(chunks).toString('utf8')).toBe('\uFEFFgenero,total\r\nDrama,42\r\n')
  })

  for (const fails of [false, true]) test(`copiar com permissão ${fails ? 'negada' : 'permitida'}`, async ({ page }) => {
    await page.addInitScript(shouldFail => {
      Object.defineProperty(navigator, 'clipboard', { value: { writeText: async (value: string) => {
        if (shouldFail) throw new DOMException('Negado')
        Object.assign(window, { copiedText: value })
      } } })
    }, fails)
    await page.route('**/api/perguntas', route => route.fulfill({ json: rankingAnswer }))
    await page.goto('/')
    await page.getByRole('textbox', { name: 'Sua pergunta' }).fill('Avatar')
    await page.getByRole('button', { name: 'Consultar →' }).click()
    await page.getByRole('button', { name: 'Copiar resposta' }).click()
    await expect(page.getByRole('status')).toContainText(fails ? 'Selecione o texto' : 'Resposta copiada')
    expect((await page.getByRole('status').boundingBox())?.height).toBeGreaterThan(8)
    if (!fails) expect(await page.evaluate(() => (window as Window & { copiedText?: string }).copiedText)).toBe(rankingAnswer.resposta)
    await expect(page.getByText(rankingAnswer.resposta, { exact: true })).toBeVisible()
  })
})

test.describe('consulta e recuperação', () => {
  test('seis sugestões preenchem e focam o campo sem enviar', async ({ page }) => {
    let posts = 0
    await page.route('**/api/perguntas', route => { posts++; return route.fulfill({ json: rankingAnswer }) })
    await page.goto('/')
    const suggestions = [
      'Quais são os 5 filmes com maior bilheteria em dólares?',
      'Quais são os 5 filmes mais populares?',
      'Quais são os 5 filmes com maior nota no IMDb?',
      'Qual filme recebeu mais avaliações de usuários?',
      'Quantos filmes existem por gênero?',
      'Qual diretor tem a maior média IMDb, considerando pelo menos 5 filmes?',
    ]
    const input = page.getByRole('textbox', { name: 'Sua pergunta' })
    for (const suggestion of suggestions) {
      await page.getByRole('button', { name: suggestion, exact: true }).click()
      await expect(input).toHaveValue(suggestion)
      await expect(input).toBeFocused()
    }
    expect(posts).toBe(0)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.getByRole('button', { name: 'Consultar →' }).click()
    await expect(page.getByText(rankingAnswer.resposta, { exact: true })).toBeVisible()
    expect(posts).toBe(1)
  })
  test('exemplo só preenche, bloqueia duplicata e mostra a resposta', async ({ page }) => {
    const posts: unknown[] = []
    let finish!: () => void
    const gate = new Promise<void>(resolve => { finish = resolve })
    await page.route('**/api/perguntas', async route => {
      posts.push(route.request().postDataJSON())
      await gate
      await route.fulfill({ json: rankingAnswer })
    })
    await page.goto('/')
    await page.getByRole('button', { name: 'Quais são os 5 filmes com maior bilheteria em dólares?', exact: true }).click()
    expect(posts).toHaveLength(0)
    const input = page.getByRole('textbox', { name: 'Sua pergunta' })
    await expect(input).toBeFocused()
    await input.press('Enter')
    await expect(page.getByRole('button', { name: 'Consultando…' })).toBeDisabled()
    await input.press('Enter')
    expect(posts).toEqual([{ pergunta: 'Quais são os 5 filmes com maior bilheteria em dólares?' }])
    finish()
    await expect(page.getByText(rankingAnswer.resposta, { exact: true })).toBeVisible()
  })

  test('Shift+Enter e IME não enviam; HTML do modelo é texto', async ({ page }) => {
    const posts: unknown[] = []
    await page.route('**/api/perguntas', async route => {
      posts.push(route.request().postDataJSON())
      await route.fulfill({ json: { ...rankingAnswer, resposta: '<img src=x onerror=alert(1)>' } })
    })
    await page.goto('/')
    const input = page.getByRole('textbox', { name: 'Sua pergunta' })
    await input.fill('Avatar')
    await input.press('Shift+Enter')
    await expect(input).toHaveValue('Avatar\n')
    await input.dispatchEvent('keydown', { key: 'Enter', code: 'Enter', isComposing: true })
    expect(posts).toHaveLength(0)
    await page.getByRole('button', { name: 'Consultar →' }).click()
    await expect(page.getByText('<img src=x onerror=alert(1)>', { exact: true })).toBeVisible()
    await expect(page.locator('[onerror]')).toHaveCount(0)
  })

  for (const [status, answer] of Object.entries(statusAnswers)) test(`apresenta o status ${status}`, async ({ page }) => {
    await page.route('**/api/perguntas', route => route.fulfill({ json: answer }))
    await page.goto('/')
    await page.getByRole('textbox', { name: 'Sua pergunta' }).fill('Avatar')
    await page.getByRole('button', { name: 'Consultar →' }).click()
    await expect(page.getByText(answer.resposta, { exact: true })).toBeVisible()
  })

  for (const [httpStatus, code] of [[422, 'entrada_invalida'], [503, 'banco_indisponivel'], [503, 'configuracao_invalida'], [503, 'modelo_indisponivel'], [503, 'cota_excedida'], [502, 'resposta_invalida'], [504, 'prazo_excedido']] as const) {
    test(`preserva entrada e só tenta novamente por ação explícita: ${code}`, async ({ page }) => {
      let calls = 0
      await page.route('**/api/perguntas', async route => {
        calls++
        await route.fulfill(calls === 1 ? { status: httpStatus, json: { detail: { codigo: code, mensagem: 'private detail' } } } : { json: rankingAnswer })
      })
      await page.goto('/')
      await page.getByRole('textbox', { name: 'Sua pergunta' }).fill('Avatar')
      await page.getByRole('button', { name: 'Consultar →' }).click()
      await expect(page.getByRole('alert')).toBeVisible()
      await expect(page.getByRole('textbox', { name: 'Sua pergunta' })).toHaveValue('Avatar')
      expect(calls).toBe(1)
      await expect(page.getByText('private detail')).toHaveCount(0)
      await page.getByRole('button', { name: 'Tentar novamente' }).click()
      await expect(page.getByText(rankingAnswer.resposta, { exact: true })).toBeVisible()
      expect(calls).toBe(2)
    })
  }
})

test.describe('estrutura e tema', () => {
  test('apresenta a consulta sem resultados fictícios e persiste o tema escolhido', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'light' })
    await page.goto('/')
    await expect(page.getByRole('heading', { level: 1 })).toContainText('O cinema tem histórias.')
    await expect(page.getByText('cinedata', { exact: true })).toBeVisible()
    await expect(page.getByRole('table')).toHaveCount(0)
    await page.getByRole('button', { name: 'Ativar modo escuro' }).click()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
    await page.reload()
    await expect(page.getByRole('button', { name: 'Ativar modo claro' })).toBeVisible()
    await expect(page.locator('meta[name="theme-color"]')).toHaveAttribute('content', '#1B1819')
  })

  test('acompanha preferência do sistema até a escolha explícita', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' })
    await page.goto('/')
    await expect(page.getByRole('button', { name: 'Ativar modo claro' })).toBeVisible()
    await page.emulateMedia({ colorScheme: 'light' })
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
    await page.getByRole('button', { name: 'Ativar modo escuro' }).click()
    await page.emulateMedia({ colorScheme: 'light' })
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  })

  test('funciona quando o storage é bloqueado', async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(window, 'localStorage', { get() { throw new DOMException('Bloqueado', 'SecurityError') } })
    })
    await page.emulateMedia({ colorScheme: 'light' })
    await page.goto('/')
    await page.getByRole('button', { name: 'Ativar modo escuro' }).click()
    await expect(page.getByRole('button', { name: 'Ativar modo claro' })).toBeVisible()
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  })

  test('mantém marca e ações acessíveis em 320 px', async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 812 })
    await page.emulateMedia({ colorScheme: 'light' })
    await page.goto('/')
    const toggle = page.getByRole('button', { name: 'Ativar modo escuro' })
    await expect(toggle).toBeVisible()
    expect((await toggle.boundingBox())?.width).toBe(48)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await toggle.focus()
    await page.keyboard.press('Enter')
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  })
})
