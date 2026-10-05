import { useEffect, useId, useRef, type ReactNode } from 'react'

export default function Modal({
  open,
  title,
  onClose,
  children,
  drawer = false,
}: {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
  drawer?: boolean
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  useEffect(() => {
    const dialog = ref.current
    if (open && dialog && !dialog.open) dialog.showModal()
    else if (!open && dialog?.open) dialog.close()
  }, [open])
  return (
    <dialog
      ref={ref}
      className={`dialog${drawer ? ' dialog-drawer' : ''}`}
      aria-labelledby={titleId}
      onClose={onClose}
      onKeyDown={(event) => {
        if (event.key !== 'Tab') return
        const controls = Array.from(
          event.currentTarget.querySelectorAll<HTMLElement>(
            'button:not([disabled]), a[href], input:not([disabled]), textarea:not([disabled]), summary, [tabindex="0"]',
          ),
        ).filter((element) => element.getClientRects().length > 0)
        const first = controls[0],
          last = controls.at(-1)
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault()
          last?.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first?.focus()
        }
      }}
    >
      <div className="dialog-header">
        <h2 id={titleId}>{title}</h2>
        <button
          className="secondary"
          onClick={() => ref.current?.close()}
          aria-label={`Fechar ${title}`}
        >
          Fechar
        </button>
      </div>
      {open && children}
    </dialog>
  )
}
