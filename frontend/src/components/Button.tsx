import { Link } from 'react-router-dom'
import type { ReactNode } from 'react'

const base =
  'inline-flex h-11 items-center justify-center rounded-lg px-4 py-2.5 text-sm font-semibold transition-opacity disabled:opacity-50'

const variants = {
  primary: 'bg-action text-on-action hover:opacity-90',
  secondary:
    'border border-border bg-surface text-brand hover:bg-brand-soft',
  danger: 'bg-danger text-on-action hover:opacity-90',
}

type Props = {
  variant?: keyof typeof variants
  className?: string
  children: ReactNode
  disabled?: boolean
  type?: 'button' | 'submit'
  onClick?: () => void
}

export function Button({
  variant = 'primary',
  className = '',
  children,
  disabled,
  type = 'button',
  onClick,
}: Props) {
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`${base} ${variants[variant]} ${className}`}
    >
      {children}
    </button>
  )
}

export function ButtonLink({
  to,
  variant = 'secondary',
  className = '',
  children,
}: {
  to: string
  variant?: keyof typeof variants
  className?: string
  children: ReactNode
}) {
  return (
    <Link to={to} className={`${base} ${variants[variant]} ${className}`}>
      {children}
    </Link>
  )
}
