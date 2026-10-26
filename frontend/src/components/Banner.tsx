type Variant = 'warning' | 'danger' | 'success' | 'info'

const styles: Record<Variant, string> = {
  warning: 'bg-warning-soft text-warning border-warning/30',
  danger: 'bg-danger-soft text-danger border-danger/30',
  success: 'bg-success-soft text-success border-success/30',
  info: 'bg-brand-soft text-brand border-brand/30',
}

export function Banner({
  children,
  variant = 'info',
}: {
  children: React.ReactNode
  variant?: Variant
}) {
  return (
    <div
      role="status"
      className={`rounded-lg border px-3 py-2 text-sm ${styles[variant]}`}
    >
      {children}
    </div>
  )
}
