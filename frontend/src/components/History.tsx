import { useEffect, useRef } from 'react'
import type { HistoryEntry } from '../types'
import { Brand } from './Brand'
import { Icon } from './Icon'

const statuses = { resultado: 'Resultado', esclarecimento: 'Esclarecimento', sem_dados: 'Sem dados', recusa: 'Recusa' }
interface Props {
  entries: HistoryEntry[]; activeId: string | null; open: boolean; onClose: () => void
  onSelect: (entry: HistoryEntry) => void; onNew: () => void; loading: boolean
  paused: boolean; onPause: () => void
}

function HistoryContent({ entries, activeId, onSelect, onNew, loading, paused, onPause }: Omit<Props, 'open' | 'onClose'>) {
  return <div className="history-content">
    <Brand />
    <button type="button" className="button button-primary new-question" disabled={loading} onClick={onNew}><Icon name="plus" />Nova consulta</button>
    <div className="history-heading"><h2>Histórico da sessão</h2><span>{entries.length}</span></div>
    {entries.length === 0 ? <div className="history-empty"><Icon name="history" /><p>Suas consultas aparecerão aqui.</p><p>Revisite uma resposta sem consultar de novo.</p></div>
      : <nav aria-label="Consultas anteriores"><ol className="history-list">
        {entries.map(entry => <li key={entry.id}><button type="button" className={`history-entry ${activeId === entry.id ? 'is-selected' : ''}`}
          aria-label={`Revisitar: ${entry.pergunta}`} aria-current={activeId === entry.id ? 'true' : undefined} disabled={loading} onClick={() => onSelect(entry)}>
          <span className="history-question">{entry.pergunta}</span>
          <span className="history-meta"><span>{entry.error ? 'Erro' : statuses[entry.response!.status]}</span>
            <time dateTime={new Date(entry.createdAt).toISOString()}>{new Date(entry.createdAt).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</time>
          </span>
        </button></li>)}
      </ol></nav>}
    {loading && <p className="pending-note">Aguarde a consulta terminar para selecionar outra.</p>}
    <div className="sidebar-footer"><p className="session-note"><Icon name="info" /><span><strong>Perguntas independentes</strong>Histórico só nesta sessão. Ao recarregar, ele é apagado.</span></p>
      <button type="button" className="button button-secondary motion-toggle" aria-pressed={paused} onClick={onPause}><Icon name={paused ? 'play' : 'pause'} />{paused ? 'Retomar animação' : 'Pausar animação'}</button>
    </div>
  </div>
}

export function History({ open, onClose, ...props }: Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const drawer = dialog.current!
    if (open && !drawer.open) drawer.showModal()
    if (!open && drawer.open) drawer.close()
  }, [open])
  useEffect(() => {
    const desktop = window.matchMedia('(min-width: 768px)')
    const closeOnDesktop = () => { if (desktop.matches) onClose() }
    desktop.addEventListener('change', closeOnDesktop)
    return () => desktop.removeEventListener('change', closeOnDesktop)
  }, [onClose])
  function act(action: () => void) { dialog.current?.close(); onClose(); action() }
  return <>
    <aside className="session-panel" aria-label="Histórico da sessão"><HistoryContent {...props} /></aside>
    <dialog id="session-drawer" className="history-drawer" ref={dialog} aria-labelledby="drawer-title" onCancel={onClose} onClose={onClose}>
      <div className="drawer-header"><h2 id="drawer-title">Histórico da sessão</h2><button type="button" className="button button-quiet" aria-label="Fechar histórico" autoFocus onClick={() => act(() => {})}><Icon name="close" /></button></div>
      <HistoryContent {...props} onSelect={entry => act(() => props.onSelect(entry))} onNew={() => act(props.onNew)} />
    </dialog>
  </>
}
