import type { ReactNode } from 'react'

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-border bg-surface px-6 py-10 text-center">
      <p className="font-medium text-text">{title}</p>
      {children ? <p className="mt-2 text-sm text-muted">{children}</p> : null}
    </div>
  )
}
