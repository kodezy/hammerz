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
    <div className="flex flex-wrap gap-x-5 gap-y-1 border-b border-border sm:gap-x-8">
      {tabs.map((t) => {
        const isActive = t.key === active
        return (
          <button
            key={t.key}
            type="button"
            onClick={() => onChange(t.key)}
            className={`-mb-px shrink-0 border-b-2 pb-3 text-[15px] font-semibold whitespace-nowrap transition-colors ${
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
