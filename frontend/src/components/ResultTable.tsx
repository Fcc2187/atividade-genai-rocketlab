import type { Evidence } from '../types'
import { columnLabel, formatValue } from '../valueFormatting'

export default function ResultTable({ evidence, index, raw = false }: { evidence: Evidence; index: number; raw?: boolean }) {
  return <div className="table-scroll" role="region" aria-label={`${raw ? 'Valores originais' : 'Tabela'} da consulta ${index}`} tabIndex={0}>
    <table><caption>{raw ? 'Dados originais recebidos' : 'Dados recebidos'} da consulta {index}</caption>
      <thead><tr>{evidence.colunas.map((column, i) => <th scope="col" key={i}>{raw ? column : columnLabel(column)}</th>)}</tr></thead>
      <tbody>{evidence.linhas.map((row, i) => <tr key={i}>{row.map((value, j) => <td key={j}>{value === null ? <span className="muted">Não informado</span> : value === '' ? <span className="muted">Texto vazio</span> : raw ? String(value) : formatValue(value, evidence.colunas[j])}</td>)}</tr>)}</tbody>
    </table>
    {evidence.linhas.length === 0 && <p className="small muted">Nenhuma linha recebida nesta consulta.</p>}
  </div>
}
