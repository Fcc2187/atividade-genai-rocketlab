import type { RefObject } from 'react'

type Props = { value: string; onChange: (value: string) => void; onSubmit: () => void; pending: boolean; error: string | null; inputRef: RefObject<HTMLTextAreaElement | null> }
export default function QuestionForm({ value, onChange, onSubmit, pending, error, inputRef }: Props) {
  const count = Array.from(value.trim()).length
  const validation = count > 2000 ? 'O limite é de 2.000 caracteres. Encurte sua pergunta para consultar.' : null
  const currentError = error ?? validation
  return <form className="question-form" onSubmit={event => { event.preventDefault(); onSubmit() }}>
    <label htmlFor="question">Sua pergunta</label>
    <textarea id="question" ref={inputRef} value={value} rows={1} readOnly={pending}
      placeholder="O que você quer descobrir sobre cinema?" aria-describedby={`question-help${currentError ? ' question-error' : ''}`}
      aria-invalid={!!currentError} onChange={event => onChange(event.target.value)}
      onKeyDown={event => {
        if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && event.keyCode !== 229) { event.preventDefault(); if (!pending && count > 0 && count <= 2000) onSubmit() }
      }} />
    <div className="form-actions">
      <p id="question-help" className="small muted">Até 2.000 caracteres <span className="keyboard-help">· Enter para enviar · Shift+Enter para nova linha</span><span className="counter">{count.toLocaleString('pt-BR')}/2.000</span></p>
      <button type="submit" disabled={pending || count === 0 || count > 2000}>{pending ? 'Consultando…' : 'Consultar →'}</button>
    </div>
    {currentError && <div id="question-error" className="error-panel" role="alert"><p>{currentError}</p><p className="small">Sua pergunta foi preservada.</p>{error && <button type="button" className="secondary" disabled={pending || count === 0 || count > 2000} onClick={onSubmit}>Tentar novamente</button>}</div>}
  </form>
}
