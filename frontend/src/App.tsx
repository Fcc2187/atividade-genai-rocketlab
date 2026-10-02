import { useEffect, useRef, useState } from 'react'
import { ApiError, askQuestion, checkHealth } from './api'
import type { HistoryEntry } from './types'
import { Background } from './components/Background'
import { Brand, BrandMark } from './components/Brand'
import { Examples } from './components/Examples'
import { History } from './components/History'
import { Icon } from './components/Icon'
import { Loading } from './components/Loading'
import { QuestionForm } from './components/QuestionForm'
import { Result } from './components/Result'

export default function App() {
  const [pergunta, setPergunta] = useState('')
  const [validation, setValidation] = useState<string | null>(null)
  const [entries, setEntries] = useState<HistoryEntry[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [pending, setPending] = useState<number | null>(null)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [paused, setPaused] = useState(false)
  const [bank, setBank] = useState<'checking' | 'ready' | 'unavailable'>('checking')
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const requestInFlight = useRef(false)
  const questionController = useRef<AbortController | null>(null)
  const active = entries.find(entry => entry.id === activeId)

  useEffect(() => {
    let mounted = true
    const healthController = new AbortController()
    checkHealth(healthController.signal).then(() => { if (mounted) setBank('ready') }).catch(() => { if (mounted) setBank('unavailable') })
    return () => { mounted = false; healthController.abort(); questionController.current?.abort() }
  }, [])

  function edit(text: string) {
    if (requestInFlight.current) return
    setPergunta(text); setValidation(null); setHistoryOpen(false)
    inputRef.current?.focus()
  }
  function newQuestion() {
    if (!requestInFlight.current) {
      setActiveId(null); edit('')
      requestAnimationFrame(() => inputRef.current?.focus())
    }
  }
  function select(entry: HistoryEntry) {
    if (requestInFlight.current) return
    setActiveId(entry.id); setPergunta(entry.pergunta); setValidation(null); setHistoryOpen(false)
  }
  async function submit() {
    if (requestInFlight.current) return
    const trimmed = pergunta.trim()
    if (!trimmed || Array.from(trimmed).length > 2000) {
      setValidation(!trimmed ? 'Escreva uma pergunta para consultar o catálogo.' : 'Use no máximo 2000 caracteres na pergunta.')
      inputRef.current?.focus(); return
    }
    requestInFlight.current = true
    const controller = new AbortController()
    questionController.current = controller
    const start = performance.now()
    setPending(start); setActiveId(null); setValidation(null); setHistoryOpen(false)
    const entry: HistoryEntry = { id: crypto.randomUUID(), pergunta: trimmed, createdAt: Date.now(), duration: 0 }
    try { entry.response = await askQuestion(trimmed, controller.signal) }
    catch (error) {
      const failure = error instanceof ApiError ? error : new ApiError('resposta_invalida')
      entry.error = { code: failure.code, message: failure.message }
    } finally {
      entry.duration = (performance.now() - start) / 1000
      if (!controller.signal.aborted) {
        setEntries(previous => [entry, ...previous]); setActiveId(entry.id)
        setPending(null)
      }
      questionController.current = null; requestInFlight.current = false
    }
  }

  const showingResult = pending !== null || !!active
  const form = <QuestionForm value={pergunta} onChange={value => { setPergunta(value); setValidation(null) }} onSubmit={submit} loading={pending !== null} error={validation} inputRef={inputRef} followup={showingResult} />
  return <>
    <Background paused={paused} />
    <a href="#consulta" className="skip-link">Ir para a consulta</a>
    <div className="app-shell">
      <History entries={entries} activeId={activeId} open={historyOpen} onClose={() => setHistoryOpen(false)} onSelect={select} onNew={newQuestion} loading={pending !== null} paused={paused} onPause={() => setPaused(!paused)} />
      <header className="mobile-header"><Brand /><button type="button" className="button button-secondary" aria-controls="session-drawer" aria-haspopup="dialog" aria-expanded={historyOpen} onClick={() => setHistoryOpen(true)}><Icon name="history" />Histórico</button></header>
      <main id="consulta" tabIndex={-1} className={`main-content ${showingResult ? 'view-results' : 'view-home'}`}>
        <div className="catalog-label"><Icon name="book" /><span>Catálogo de filmes · Somente leitura</span></div>
        {showingResult ? <>
          <header className="results-header"><h1>Explore o catálogo</h1><p>Respostas em português, com os dados por trás de cada consulta.</p></header>
          <div className="results-layout">
            <div className="consultation-column">
              <div className="question-bubble"><Icon name="search" /><p>{active?.pergunta ?? pergunta.trim()}</p></div>
              <div className="result-area" aria-busy={pending !== null}>{pending !== null ? <Loading startedAt={pending} /> : active && <Result key={active.id} entry={active} onEdit={() => edit(active.pergunta)} disabled={false} />}</div>
              {form}
            </div>
            <aside className="catalog-auxiliary" aria-label="Explorar o catálogo">
              <Examples onChoose={edit} disabled={pending !== null} auxiliary />
              <div className="consultation-note"><h2>Sobre esta consulta</h2><p><Icon name="book" />O catálogo é consultado somente para leitura.</p><p><Icon name="info" />Perguntas independentes, sem memória de conversas.</p></div>
            </aside>
          </div>
        </> : <div className="welcome-content">
          <header className="intro"><BrandMark className="welcome-mark" /><h1>O que você quer<br className="desktop-break" /> descobrir?</h1><p>Explore filmes, descubra relações e encontre respostas.<br className="desktop-break" /> Pergunte em português. Os dados contam o resto.</p></header>
          {form}
          <Examples onChoose={edit} disabled={false} />
        </div>}
        <footer className="workspace-footer"><div className="bank-status"><span className="status-dot" aria-hidden="true" /><span>{bank === 'ready' ? 'Banco disponível' : bank === 'checking' ? 'Verificando banco…' : 'Banco indisponível'}</span><span className="bank-explanation">Essa verificação não verifica o Groq.</span></div><span>CineData Analytics · RocketLab</span></footer>
        <p className="sr-only" role="status">{pending === null && active ? active.error ? 'A consulta terminou com erro.' : 'Resposta disponível na área de resultados.' : ''}</p>
      </main>
    </div>
  </>
}
