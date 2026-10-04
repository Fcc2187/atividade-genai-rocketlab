import type { Answer } from '../types'
import FilmResults from './FilmResults'
import Evidence from './Evidence'
import { useState } from 'react'

const titles = { resultado: 'Resposta do catálogo', esclarecimento: 'Esclarecimento', recusa: 'Recusa', sem_dados: 'Sem dados' }
export default function Result({ answer, onFeedback }: { answer: Answer; onFeedback: (message: string) => void }) {
  const [copyFeedback, setCopyFeedback] = useState<{ message: string; sequence: number }>({ message: '', sequence: 0 })
  async function copy() {
    let message: string
    try { await navigator.clipboard.writeText(answer.resposta); message = 'Resposta copiada.' }
    catch { message = 'Não foi possível copiar automaticamente. Selecione o texto da resposta e copie manualmente.' }
    setCopyFeedback(previous => ({ message, sequence: previous.sequence + 1 }))
    onFeedback(message)
  }
  return <div className="results">
    <section className="result" aria-label="Resultado da consulta">
    <div className="result-intro"><h2>{titles[answer.status]}</h2><p className="answer-text">{answer.resposta}</p>
      <div className="result-actions"><button className="secondary" onClick={copy}>Copiar resposta</button></div>
      <div role="status" aria-live="polite" aria-atomic="true">{copyFeedback.message && <p className="action-feedback" key={copyFeedback.sequence}>{copyFeedback.message}</p>}</div>
    </div>
    {answer.consultas.map((evidence, i) => <FilmResults evidence={evidence} index={i + 1} key={i} />)}
    {answer.avisos.length > 0 && <div className="result-intro warnings"><h3>Limites e avisos</h3><ul>{answer.avisos.map((warning, i) => <li key={i}>{warning}</li>)}</ul></div>}
    <details className="metadata"><summary>Modelo e uso</summary><p className="small">Modelo: {answer.modelo}</p><dl>{Object.entries(answer.uso).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value ?? 'Não informado'}</dd></div>)}</dl></details>
    </section>
    {answer.consultas.length > 0 && <details className="evidence-disclosure"><summary><span>Como chegamos à resposta</span><span className="summary-action">Ver SQL e dados</span></summary><div className="evidence-content">{answer.consultas.map((evidence, i) => <Evidence evidence={evidence} index={i + 1} onFeedback={onFeedback} key={i} />)}</div></details>}
  </div>
}
