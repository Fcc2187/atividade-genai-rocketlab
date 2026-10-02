import { useEffect, useState } from 'react'

export function Loading({ startedAt }: { startedAt: number }) {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    const timer = window.setInterval(() => setSeconds(Math.floor((performance.now() - startedAt) / 1000)), 1000)
    return () => window.clearInterval(timer)
  }, [startedAt])
  return <section className="processing surface" aria-busy="true" aria-label="Consulta em processamento">
    <div className="spinner" aria-hidden="true" />
    <div><h2 role="status">Consultando o catálogo</h2><p>A resposta aparecerá aqui quando estiver pronta.</p></div>
    <span className="elapsed" aria-label="Tempo decorrido" aria-live="off">{String(Math.floor(seconds / 60)).padStart(2, '0')}:{String(seconds % 60).padStart(2, '0')}</span>
  </section>
}
