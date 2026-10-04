import type { HistoryEntry } from '../types'

const labels = { resultado: 'Resultado', esclarecimento: 'Esclarecimento', recusa: 'Recusa', sem_dados: 'Sem dados' }
type Props = { entries: HistoryEntry[]; selectedId: string | null; pending: boolean; onSelect: (id: string) => void; onNewQuestion: () => void }
export default function History({ entries, selectedId, pending, onSelect, onNewQuestion }: Props) {
  return <nav className="history" aria-label="Histórico da aba">
    <p className="eyebrow muted">SESSÃO ATUAL</p>
    <button className="secondary" disabled={pending} onClick={onNewQuestion}>＋ Nova pergunta</button>
    <p className="eyebrow muted">HISTÓRICO DA ABA</p>
    {entries.length === 0 ? <p className="small muted">Nenhuma pergunta nesta aba.</p> : <ul className="history-list">{entries.map(entry => <li key={entry.id}><button className="secondary history-item" disabled={pending} aria-current={entry.id === selectedId ? true : undefined} aria-label={entry.pergunta} onClick={() => onSelect(entry.id)}><span>{entry.pergunta}</span><span className="small muted">{labels[entry.answer.status]}</span></button></li>)}</ul>}
    <p className="small muted">Suas perguntas ficam nesta aba. Ao recarregar, o histórico é limpo.</p><hr />
    <p className="small muted">Cada pergunta é independente. O histórico não acrescenta contexto.</p>
  </nav>
}
