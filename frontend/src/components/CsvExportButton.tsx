import { useState } from 'react'
import type { Evidence } from '../types'
import { downloadCsv } from '../csv'

export default function CsvExportButton({ evidence, index, onFeedback }: { evidence: Evidence; index: number; onFeedback: (message: string) => void }) {
  const [feedback, setFeedback] = useState<{ message: string; sequence: number }>({ message: '', sequence: 0 })
  function exportCsv() {
    let message: string
    try { downloadCsv(evidence, index); message = `CSV gerado: ${evidence.linhas.length} linhas recebidas.${evidence.truncado ? ' Resultado truncado; a exportação contém somente estas linhas.' : ''}` }
    catch { message = 'Não foi possível gerar o CSV. Tente novamente.' }
    setFeedback(previous => ({ message, sequence: previous.sequence + 1 })); onFeedback(message)
  }
  return <div className="csv-export"><button className="secondary" onClick={exportCsv} aria-label={`Exportar CSV da consulta ${index}`}>Exportar CSV</button><div role="status" aria-label={`Feedback de exportação da consulta ${index}`} aria-live="polite" aria-atomic="true">{feedback.message && <p className="action-feedback" key={feedback.sequence}>{feedback.message}</p>}</div></div>
}
