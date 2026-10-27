type Tab<T extends string> = { key: T; label: string }

export function TabNav<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: Tab<T>[]
  active: T
  onChange: (key: T) => void
}) {
  return (
    <div className="flex flex-wrap gap-8 border-b border-border">
      {tabs.map((t) => {
        const isActive = t.key === active
        return (
          <button
            key={t.key}
            type="button"
            onClick={() => onChange(t.key)}
            className={`-mb-px border-b-2 pb-3 text-[15px] font-semibold transition-colors ${
              isActive
                ? 'border-brand text-text'
                : 'border-transparent text-muted hover:text-text'
            }`}
          >
            {t.label}
          </button>
        )
      })}
    </div>
  )
}
