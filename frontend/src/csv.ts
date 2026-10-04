import type { Evidence, SQLValue } from './types'

function cell(value: SQLValue): string {
  let text = value === null ? '' : String(value)
  if (typeof value === 'string' && (/^[\s\uFEFF]*[=+\-@]/u.test(text) || /^[\t\r\n]/u.test(text))) text = "'" + text
  return /[",\r\n]/u.test(text) ? '"' + text.replaceAll('"', '""') + '"' : text
}
export function toCsv(evidence: Evidence): string {
  return '\uFEFF' + [evidence.colunas, ...evidence.linhas].map(row => row.map(cell).join(',')).join('\r\n') + '\r\n'
}
export function downloadCsv(evidence: Evidence, index: number): void {
  const url = URL.createObjectURL(new Blob([toCsv(evidence)], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `cinedata-consulta-${index}${evidence.truncado ? '-truncada' : ''}.csv`
  document.body.append(link)
  try { link.click() } finally { link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000) }
}
