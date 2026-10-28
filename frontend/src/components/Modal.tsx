import { useEffect, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

export function Modal({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
}) {
  useEffect(() => {
    if (!open) return
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => {
      document.body.style.overflow = prevOverflow
      document.removeEventListener('keydown', onKey)
    }
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div className="fixed inset-0 z-[100] min-h-dvh">
      <button
        type="button"
        className="absolute inset-0 bg-scrim"
        aria-label="Close dialog"
        onClick={onClose}
      />
      <div className="relative flex min-h-dvh items-center justify-center p-6 pointer-events-none">
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
          className="pointer-events-auto max-h-[min(90dvh,100%)] w-full max-w-lg overflow-y-auto rounded-xl border border-border bg-surface p-6"
        >
          <h2 id="modal-title" className="font-semibold text-text">
            {title}
          </h2>
          {children}
        </div>
      </div>
    </div>,
    document.body,
  )
}
