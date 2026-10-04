import type { Evidence as QueryEvidence } from '../types'
import { downloadCsv } from '../csv'
import { useState } from 'react'
import ResultTable from './ResultTable'

export default function Evidence({ evidence, index, onFeedback }: { evidence: QueryEvidence; index: number; onFeedback: (message: string) => void }) {
  const [feedback, setFeedback] = useState('')
  function exportCsv() {
    let message: string
    try { downloadCsv(evidence, index); message = `CSV gerado: ${evidence.linhas.length} linhas recebidas.${evidence.truncado ? ' Resultado truncado; a exportação contém somente estas linhas.' : ''}` }
    catch { message = 'Não foi possível gerar o CSV. Tente novamente.' }
    setFeedback(message); onFeedback(message)
  }
  return <section className="evidence-card" aria-label={`Evidência da consulta ${index}`}>
    <h3>Consulta {index}</h3>
    <p className={`small ${evidence.truncado ? 'truncation' : 'received'}`}>{evidence.linhas.length} linhas recebidas · {evidence.truncado ? 'Resultado truncado; estes dados não contêm todo o conjunto.' : 'Resultado completo'}</p>
    <ResultTable evidence={evidence} index={index} raw />
    <details className="sql-details"><summary>SQL e parâmetros</summary><pre>{evidence.sql}</pre><h4>Parâmetros</h4><pre>{JSON.stringify(evidence.parametros, null, 2)}</pre></details>
    <button className="secondary" onClick={exportCsv} aria-label={`Exportar CSV da consulta ${index}`}>Exportar CSV</button>
    {feedback && <p className="action-feedback" role="status">{feedback}</p>}
  </section>
}
