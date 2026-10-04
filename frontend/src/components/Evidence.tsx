import type { Evidence as QueryEvidence } from '../types'
import ResultTable from './ResultTable'

export default function Evidence({ evidence, index }: { evidence: QueryEvidence; index: number }) {
  return <section className="evidence-card" aria-label={`Evidência da consulta ${index}`}>
    <h3>Consulta {index}</h3>
    <p className={`small ${evidence.truncado ? 'truncation' : 'received'}`}>{evidence.linhas.length} linhas recebidas · {evidence.truncado ? 'Resultado truncado; estes dados não contêm todo o conjunto.' : 'Resultado completo'}</p>
    <ResultTable evidence={evidence} index={index} raw />
    <details className="sql-details"><summary>SQL e parâmetros</summary><pre>{evidence.sql}</pre><h4>Parâmetros</h4><pre>{JSON.stringify(evidence.parametros, null, 2)}</pre></details>
  </section>
}
