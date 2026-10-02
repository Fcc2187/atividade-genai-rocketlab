import { useState } from 'react'
import { toCsv } from '../csv'
import type { HistoryEntry, QueryEvidence, SqlValue } from '../types'
import { Icon } from './Icon'

const titles = { resultado: 'Resultado da consulta', esclarecimento: 'Precisamos de um detalhe', sem_dados: 'Nenhum dado encontrado', recusa: 'Consulta não permitida' }
const usageLabels: Record<string, string> = { chamadas: 'Chamadas ao modelo', tokens_entrada: 'Tokens de entrada', tokens_saida: 'Tokens de saída', tentativas_sql: 'Tentativas SQL' }

function cell(value: SqlValue) {
  return value === null ? <span className="empty-cell" role="img" aria-label="Sem valor">—</span> : value === '' ? <span className="empty-cell">Texto vazio</span> : String(value)
}

function Evidence({ evidence, index }: { evidence: QueryEvidence; index: number }) {
  function download() {
    const url = URL.createObjectURL(new Blob([toCsv(evidence)], { type: 'text/csv;charset=utf-8' }))
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `cinedata-consulta-${index}.csv`
    anchor.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  return <section className="evidence" aria-labelledby={`evidence-title-${index}`}>
    <div className="evidence-heading flex flex-wrap items-center justify-between gap-3">
      <div className="flex flex-wrap items-center gap-3"><h3 id={`evidence-title-${index}`}>Consulta {index}</h3><span className="row-count">{evidence.linhas.length} {evidence.linhas.length === 1 ? 'linha' : 'linhas'} recebidas</span></div>
      <button type="button" className="button button-quiet" aria-label={`Exportar consulta ${index} em CSV`} onClick={download}><Icon name="download" />Exportar CSV</button>
    </div>
    {evidence.truncado && <p className="truncation"><Icon name="warning" /><span><strong>Dados parciais</strong> — esta evidência foi truncada. A tabela e o CSV contêm somente os dados recebidos.</span></p>}
    <div className="table-scroll" role="region" aria-label={`Tabela da consulta ${index}`} tabIndex={0}>
      <table><caption className="sr-only">Dados retornados pela consulta {index}</caption>
        <thead><tr>{evidence.colunas.map((column, col) => <th scope="col" key={col}>{column}</th>)}</tr></thead>
        <tbody>{evidence.linhas.map((row, number) => <tr key={number}>{row.map((value, col) => <td key={col} className={typeof value === 'number' ? 'numeric-cell' : ''}>{cell(value)}</td>)}</tr>)}</tbody>
      </table>
      {evidence.linhas.length === 0 && <p className="no-rows">Esta consulta não retornou linhas.</p>}
    </div>
    <details className="query-details"><summary>SQL e parâmetros da consulta {index}</summary>
      <div className="technical-content"><h4>SQL executado</h4><pre>{evidence.sql}</pre><h4>Parâmetros</h4><pre>{JSON.stringify(evidence.parametros, null, 2)}</pre></div>
    </details>
  </section>
}

export function Result({ entry, onEdit, disabled }: { entry: HistoryEntry; onEdit: () => void; disabled: boolean }) {
  const [copyState, setCopyState] = useState('')
  if (entry.error) return <section className="error-result surface" role="alert">
    <Icon name="warning" /><div><h2>Não foi possível concluir</h2><p>{entry.error.message}</p><p className="small-note">Sua pergunta foi preservada. Uma nova tentativa só acontece se você enviar novamente.</p></div>
  </section>
  const response = entry.response!
  async function copy() {
    try { await navigator.clipboard.writeText(response.resposta); setCopyState('Resposta copiada.') }
    catch { setCopyState('Não foi possível copiar. Selecione o texto da resposta e copie manualmente.') }
  }
  return <article className="result surface" aria-labelledby="result-title">
    <div className="result-topline flex flex-wrap items-center justify-between gap-3">
      <span className={`result-status status-${response.status}`}><Icon name={response.status === 'resultado' ? 'check' : 'info'} />{response.status === 'resultado' ? 'Consulta concluída' : 'Resposta do catálogo'}</span>
      <span className="result-duration">{entry.duration.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} s de consulta</span>
    </div>
    <h2 id="result-title">{titles[response.status]}</h2>
    <div className="answer-text">{response.resposta}</div>
    {response.avisos.length > 0 && <section className="warnings" aria-labelledby="warnings-title"><h3 id="warnings-title"><Icon name="info" />Avisos e limitações</h3><ul>{response.avisos.map((warning, index) => <li key={index}>{warning}</li>)}</ul></section>}
    <div className="result-actions flex flex-wrap items-center gap-3">
      <button type="button" className="button button-quiet" onClick={copy}><Icon name="copy" />Copiar resposta</button>
      {response.status === 'esclarecimento' && <button type="button" className="button button-secondary" onClick={onEdit} disabled={disabled}>Editar pergunta<Icon name="arrow" /></button>}
      <p role="status" className="copy-feedback">{copyState}</p>
    </div>
    {response.consultas.length > 0 && <div className="evidences">{response.consultas.map((evidence, index) => <Evidence key={index} evidence={evidence} index={index + 1} />)}</div>}
    <details className="model-details"><summary>Detalhes do modelo e uso</summary><dl>
      <div><dt>Modelo</dt><dd>{response.modelo}</dd></div>
      {Object.entries(response.uso).map(([key, value]) => <div key={key}><dt>{usageLabels[key] ?? key}</dt><dd>{value === null ? 'Não informado' : String(value)}</dd></div>)}
    </dl></details>
  </article>
}
