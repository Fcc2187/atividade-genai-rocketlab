import { useEffect, useRef, useState } from 'react'
import Header from './components/Header'
import QuestionForm from './components/QuestionForm'
import Result from './components/Result'
import History from './components/History'
import Modal from './components/Modal'
import { askQuestion, normalizeQuestion } from './api'
import type { HistoryEntry } from './types'
import { useElapsedTime } from './useElapsedTime'
import { resultTitle } from './resultPresentation'

const suggestions = [
  'Quais são os 5 filmes com maior bilheteria em dólares?',
  'Quais são os 5 filmes mais populares?',
  'Quais são os 5 filmes com maior nota no IMDb?',
  'Qual filme recebeu mais avaliações de usuários?',
  'Quantos filmes existem por gênero?',
  'Qual diretor tem a maior média IMDb, considerando pelo menos 5 filmes?',
]

export default function App() {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light')
  const explicitTheme = useRef(false)
  const [question, setQuestion] = useState('')
  const [pending, setPending] = useState(false)
  const elapsed = useElapsedTime(pending)
  const [error, setError] = useState<string | null>(null)
  const [entries, setEntries] = useState<HistoryEntry[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [feedback, setFeedback] = useState('')
  const [modal, setModal] = useState<'history' | 'help' | null>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const sending = useRef(false)
  const selected = entries.find(entry => entry.id === selectedId)
  function focusQuestion() {
    requestAnimationFrame(() => {
      inputRef.current?.focus({ preventScroll: true })
      inputRef.current?.scrollIntoView({ block: 'center' })
    })
  }
  function newQuestion() {
    if (sending.current) return
    setSelectedId(null); setQuestion(''); setError(null); setFeedback(''); setModal(null)
    focusQuestion()
  }
  function reformulate() {
    if (sending.current || !selected) return
    setQuestion(selected.pergunta); setError(null); setFeedback(''); setModal(null)
    focusQuestion()
  }
  function selectEntry(id: string) {
    if (sending.current) return
    const entry = entries.find(item => item.id === id)
    if (!entry) return
    setSelectedId(id); setQuestion(entry.pergunta); setError(null); setModal(null); setFeedback('Resposta reaberta do histórico, sem uma nova consulta.')
  }
  const historyProps = { entries, selectedId, pending, onSelect: selectEntry, onNewQuestion: newQuestion }
  async function submit() {
    if (sending.current) return
    let normalized: string
    try { normalized = normalizeQuestion(question) } catch (cause) { setError(cause instanceof Error ? cause.message : 'Revise sua pergunta.'); inputRef.current?.focus(); return }
    sending.current = true
    setPending(true); setError(null); setFeedback(''); setQuestion(normalized); setSelectedId(null)
    try {
      const answer = await askQuestion(normalized)
      const entry = { id: crypto.randomUUID(), pergunta: normalized, answer }
      setEntries(previous => [entry, ...previous]); setSelectedId(entry.id)
      setFeedback('Resposta recebida. Leia o resultado abaixo.')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Não foi possível concluir a consulta.') }
    finally { sending.current = false; setPending(false) }
  }
  useEffect(() => {
    try { explicitTheme.current = ['light', 'dark'].includes(localStorage.getItem('cinedata-theme') ?? '') } catch { /* storage is optional */ }
    const media = matchMedia('(prefers-color-scheme: dark)')
    const followSystem = () => { if (!explicitTheme.current) setTheme(media.matches ? 'dark' : 'light') }
    media.addEventListener('change', followSystem)
    return () => media.removeEventListener('change', followSystem)
  }, [])
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    document.documentElement.style.colorScheme = theme
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#1B1819' : '#F5F2EB')
  }, [theme])
  function toggleTheme() {
    const next = theme === 'light' ? 'dark' : 'light'
    explicitTheme.current = true
    try { localStorage.setItem('cinedata-theme', next) } catch { /* keep theme usable */ }
    setTheme(next)
  }
  return <>
    <a className="skip-link" href="#main">Ir para o conteúdo</a>
    <Header theme={theme} onToggleTheme={toggleTheme} onOpenHistory={() => setModal('history')} onOpenHelp={() => setModal('help')} />
    <div className="workspace">
      <aside className="sidebar"><History {...historyProps} /></aside>
      <main id="main" tabIndex={-1} className="main">
        <p className="eyebrow">CINEMA, COM EVIDÊNCIAS</p>
        <h1>{pending ? 'Consultando o catálogo' : selected ? resultTitle(selected.answer) : <>O cinema tem histórias.<br />Os dados também.</>}</h1>
        {!selected && !pending && <p className="muted">Pergunte ao catálogo e leia a resposta junto das evidências que a sustentam.</p>}
        <QuestionForm value={question} onChange={value => { setQuestion(value); setError(null) }} onSubmit={submit} pending={pending} error={error} inputRef={inputRef} />
        {!selected && !pending && !error && <div className="examples"><p className="eyebrow muted">PERGUNTAS SUGERIDAS</p><div className="suggestions-grid">{suggestions.map(suggestion => <button key={suggestion} className="secondary" onClick={() => { setQuestion(suggestion); inputRef.current?.focus() }}>{suggestion}</button>)}</div><p className="small muted">As sugestões preenchem o campo. Você escolhe quando enviar.</p></div>}
        {pending && <div className="loading-panel"><div role="status"><h2>Sua pergunta está sendo processada.</h2><p className="muted">Aguarde a resposta. O envio está temporariamente desativado.</p></div><p className="small muted">Tempo decorrido: {elapsed} s</p></div>}
        {selected && <Result key={selected.id} answer={selected.answer} onFeedback={setFeedback} onReformulate={reformulate} onNewQuestion={newQuestion} />}
        <button className="secondary mobile-help" onClick={() => setModal('help')}>Como usar</button>
        <p className="sr-only" aria-live="polite">{feedback.startsWith('Resposta recebida') || feedback.startsWith('Resposta reaberta') ? feedback : ''}</p>
      </main>
    </div>
    <Modal open={modal === 'history'} title="Histórico da aba" drawer onClose={() => setModal(null)}><History {...historyProps} /></Modal>
    <Modal open={modal === 'help'} title="Como usar o CineData" onClose={() => setModal(null)}>
      <div className="help-content"><p>Pergunte em português sobre os filmes disponíveis no catálogo. Você escolhe quando enviar; os exemplos só preenchem o campo.</p><h3>Uma pergunta por vez</h3><p>Cada pergunta é independente. Para esclarecer ou mudar um filtro, reformule a pergunta completa e consulte novamente.</p><h3>Sua sessão</h3><p>O histórico fica nesta aba e é apagado ao recarregar. Reabrir uma resposta não envia outra consulta.</p><h3>Leia as evidências</h3><p>Os dados e o CSV de cada consulta ficam no resultado. Abra “Ver SQL e dados” para conferir valores originais, SQL e parâmetros. Resultados truncados contêm somente parte do conjunto.</p><h3>Imagens e cobertura</h3><p>Pôsteres aparecem quando há imagens nos dados de filmes. Se uma imagem faltar, o nome e os valores continuam disponíveis. O catálogo pode ter cobertura incompleta; os resultados não são uma atualização em tempo real.</p></div>
    </Modal>
  </>
}
