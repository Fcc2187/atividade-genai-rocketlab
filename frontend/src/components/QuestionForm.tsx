import type { FormEvent, RefObject } from 'react'
import { Icon } from './Icon'

interface Props {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  loading: boolean
  error: string | null
  inputRef: RefObject<HTMLTextAreaElement | null>
  followup?: boolean
}

export function QuestionForm({ value, onChange, onSubmit, loading, error, inputRef, followup = false }: Props) {
  const count = Array.from(value).length
  function submit(event: FormEvent) { event.preventDefault(); onSubmit() }
  return <form className={`question-form ${followup ? 'followup-form' : ''}`} onSubmit={submit} noValidate>
    <label htmlFor="pergunta">Sua pergunta{followup && <span className="form-context" aria-hidden="true"> · Nova consulta independente</span>}</label>
    <div className={`composer ${error ? 'has-error' : ''}`}>
      <textarea id="pergunta" ref={inputRef} value={value} rows={3} disabled={loading}
        placeholder={followup ? 'Faça outra pergunta sobre o catálogo…' : 'Ex.: Quais são os 5 filmes mais populares?'}
        aria-describedby={`question-help question-count${error ? ' question-error' : ''}`}
        aria-invalid={!!error} onChange={event => onChange(event.target.value)}
        onKeyDown={event => {
          if ((event.ctrlKey || event.metaKey) && event.key === 'Enter' && !event.nativeEvent.isComposing) {
            event.preventDefault(); onSubmit()
          }
        }} />
      <div className="composer-footer">
        <span id="question-count" className={`character-count ${count > 2000 ? 'over-limit' : ''}`}>{count.toLocaleString('pt-BR')} / 2.000 caracteres</span>
        <button type="submit" className="button button-primary" disabled={loading}>
          {loading ? 'Consultando…' : 'Consultar catálogo'}<Icon name="arrow" />
        </button>
      </div>
    </div>
    {error && <p id="question-error" className="field-error" role="alert">{error}</p>}
    <p id="question-help" className="form-help">Cada pergunta é independente. Inclua nela todos os critérios que deseja consultar.</p>
  </form>
}
