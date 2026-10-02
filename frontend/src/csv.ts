import type { QueryEvidence, SqlValue } from './types'

export function toCsv(evidence: QueryEvidence): string {
  const escape = (value: SqlValue) => {
    const text = value === null ? '' : String(value)
    // Textos de catálogo podem ser interpretados como fórmulas por planilhas.
    const safe = typeof value === 'string' && /^\s*[=+\-@\t\r\n]/.test(text) ? `'${text}` : text
    return `"${safe.replaceAll('"', '""')}"`
  }
  return '\ufeff' + [evidence.colunas, ...evidence.linhas].map(row => row.map(escape).join(',')).join('\r\n') + '\r\n'
}
