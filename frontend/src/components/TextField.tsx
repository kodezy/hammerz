import type { InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from 'react'

const inputClass =
  'mt-2 w-full rounded-lg border border-control-border bg-surface px-3 py-2.5 text-sm font-normal text-text'

export function TextField({
  label,
  className = '',
  ...props
}: { label: ReactNode; className?: string } & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className={`block text-sm font-semibold text-text ${className}`}>
      {label}
      <input className={inputClass} {...props} />
    </label>
  )
}

export function TextAreaField({
  label,
  className = '',
  ...props
}: { label: ReactNode; className?: string } & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <label className={`block text-sm font-semibold text-text ${className}`}>
      {label}
      <textarea className={`${inputClass} min-h-[88px]`} {...props} />
    </label>
  )
}
