import type { Answer } from '../types'
import FilmResults from './FilmResults'
import Evidence from './Evidence'
import { useState } from 'react'
import { getFilmColumns } from '../resultPresentation'
import ResultTable from './ResultTable'
import CsvExportButton from './CsvExportButton'

const titles = { resultado: 'Resposta do catálogo', esclarecimento: 'Esclarecimento', recusa: 'Recusa', sem_dados: 'Sem dados' }
export default function Result({ answer, onFeedback, onReformulate, onNewQuestion }: { answer: Answer; onFeedback: (message: string) => void; onReformulate: () => void; onNewQuestion: () => void }) {
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
      <div className="result-actions"><button className="secondary" onClick={copy}>Copiar resposta</button>{answer.consultas.length === 1 && <CsvExportButton evidence={answer.consultas[0]} index={1} onFeedback={onFeedback} />}</div>
      <div role="status" aria-label="Feedback de cópia" aria-live="polite" aria-atomic="true">{copyFeedback.message && <p className="action-feedback" key={copyFeedback.sequence}>{copyFeedback.message}</p>}</div>
      {answer.status === 'esclarecimento' && <><p className="small muted">Complete a pergunta original e envie novamente. Cada consulta é independente.</p><button className="secondary recovery-action" onClick={onReformulate}>Reformular pergunta</button></>}
      {answer.status === 'sem_dados' && <button className="secondary recovery-action" onClick={onReformulate}>Revisar filtros</button>}
      {answer.status === 'recusa' && <button className="secondary recovery-action" onClick={onNewQuestion}>Fazer outra pergunta</button>}
    </div>
    {(answer.avisos.length > 0 || answer.consultas.some(evidence => evidence.truncado)) && <div className="result-intro warnings"><h3>Limites e avisos</h3><ul>{answer.avisos.map((warning, i) => <li key={i}>{warning}</li>)}{answer.consultas.map((evidence, i) => evidence.truncado && <li key={`truncation-${i}`} className="truncation">Consulta {i + 1}: resultado truncado. Os dados e o CSV contêm somente as {evidence.linhas.length} linhas recebidas.</li>)}</ul></div>}
    {answer.consultas.map((evidence, i) => <section className="query-result" aria-label={`Dados da consulta ${i + 1}`} key={i}>
      <h3>Dados da consulta {i + 1}</h3>
      {answer.status !== 'resultado' && <p className="small muted">Dados de contexto para esta resposta.</p>}
      {answer.status === 'resultado' && getFilmColumns(evidence) ? <FilmResults evidence={evidence} index={i + 1} /> : <ResultTable evidence={evidence} index={i + 1} />}
      {answer.consultas.length > 1 && <CsvExportButton evidence={evidence} index={i + 1} onFeedback={onFeedback} />}
    </section>)}
    <details className="metadata"><summary>Modelo e uso</summary><p className="small">Modelo: {answer.modelo}</p><dl>{Object.entries(answer.uso).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value ?? 'Não informado'}</dd></div>)}</dl></details>
    </section>
    {answer.consultas.length > 0 && <details className="evidence-disclosure"><summary><span>Como chegamos à resposta</span><span className="summary-action">Ver SQL e dados</span></summary><div className="evidence-content">{answer.consultas.map((evidence, i) => <Evidence evidence={evidence} index={i + 1} key={i} />)}</div></details>}
  </div>
}
