import type { ReactNode } from 'react'

export function PageHeading({
  title,
  subtitle,
  action,
}: {
  title: ReactNode
  subtitle?: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="font-display text-4xl font-normal text-text md:text-[40px]">{title}</h1>
        {subtitle ? <p className="mt-2 text-base text-muted">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  )
}
