import { useState } from 'react'
import type { Evidence, SQLValue } from '../types'
import { getFilmColumns } from '../resultPresentation'
import { columnLabel, formatValue } from '../valueFormatting'

function Poster({ url, title }: { url: SQLValue; title: string }) {
  const [failed, setFailed] = useState(false)
  let src: string | null = null
  if (typeof url === 'string') {
    try { const parsed = new URL(url); if (['https:', 'http:'].includes(parsed.protocol)) src = parsed.href } catch { /* missing or invalid image */ }
  }
  return src && !failed ? <img className="poster" src={src} alt={`Pôster de ${title}`} width="56" height="84" loading="lazy" onError={() => setFailed(true)} />
    : <span className="poster poster-fallback">Pôster indisponível</span>
}
export default function FilmResults({ evidence, index = 1 }: { evidence: Evidence; index?: number }) {
  const columns = evidence.colunas.map(column => column.trim().toLowerCase())
  const film = getFilmColumns(evidence)
  if (!film) return null
  const { title: titleIndex, year: yearIndex, poster: posterIndex, id: idIndex } = film
  const rows = evidence.linhas
  const metrics = columns.map((column, i) => ({ column, i })).filter(({ column, i }) => ![titleIndex, yearIndex, posterIndex, idIndex].includes(i) && column !== 'url_backdrop')
  return <div className="film-results">
    <div className="film-heading" aria-hidden="true"><span>#</span><span>FILME / PÔSTER</span><span>{metrics.length === 1 ? columnLabel(evidence.colunas[metrics[0].i]).toUpperCase() : 'DADOS DO FILME'}</span></div>
    <ol className="film-list" aria-label={`Filmes da consulta ${index}`}>
      {rows.map((row, position) => <li key={position} className="film-row">
        <span className="film-position" aria-hidden="true">{String(position + 1).padStart(2, '0')}</span>
        <Poster key={`${row[posterIndex]}-${row[titleIndex]}`} url={row[posterIndex] ?? null} title={String(row[titleIndex])} />
        <div className="film-title"><p>{row[titleIndex]}</p>{yearIndex >= 0 && row[yearIndex] !== null && <p className="small muted">{row[yearIndex]}</p>}</div>
        <dl className="film-metrics">{metrics.map(({ column, i }) => <div key={i}><dt className={metrics.length === 1 ? 'sr-only' : 'small muted'}>{columnLabel(evidence.colunas[i])}</dt><dd><span className="metric-full">{formatValue(row[i], column)}</span><span className="metric-compact" aria-hidden="true" title={formatValue(row[i], column)}>{formatValue(row[i], column, true)}</span></dd></div>)}</dl>
      </li>)}
    </ol>
  </div>
}
