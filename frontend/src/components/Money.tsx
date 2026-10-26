import { formatMoney } from '../lib/money'
import type { Money as MoneyType } from '../lib/types'

export function Money({ value, className }: { value: MoneyType | null | undefined; className?: string }) {
  return <span className={className}>{formatMoney(value)}</span>
}
