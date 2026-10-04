import { useEffect, useState } from 'react'

export function useElapsedTime(pending: boolean): number {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    setSeconds(0)
    if (!pending) return
    const started = performance.now()
    const interval = setInterval(() => setSeconds(Math.floor((performance.now() - started) / 1000)), 1000)
    return () => clearInterval(interval)
  }, [pending])
  return pending ? seconds : 0
}
