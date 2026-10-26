import { Link, useNavigate } from 'react-router-dom'
import { useSession } from '../app/session'
import { useTheme } from '../app/theme'

function ThemeToggle() {
  const { toggle, label, pressed } = useTheme()
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={label}
      aria-pressed={pressed}
      title={label}
      className="flex h-10 w-10 items-center justify-center rounded-lg border border-border text-muted hover:text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
    >
      {pressed ? '☀' : '☾'}
    </button>
  )
}

export function Shell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useSession()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
          <nav className="flex flex-wrap items-center gap-4 text-sm font-medium">
            <Link to="/" className="text-brand hover:underline">Auctions</Link>
            {user?.role === 'BIDDER' && (
              <>
                <Link to="/my-wins" className="hover:underline">My Bids &amp; Wins</Link>
                <Link to="/wallet" className="hover:underline">Wallet</Link>
              </>
            )}
            {user?.role === 'SELLER' && (
              <Link to="/seller" className="hover:underline">Seller dashboard</Link>
            )}
          </nav>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            {user ? (
              <button
                type="button"
                className="rounded-lg border border-border px-3 py-2 text-sm hover:bg-brand-soft"
                onClick={() => {
                  logout()
                  navigate('/')
                }}
              >
                Sign out
              </button>
            ) : (
              <Link
                to="/login"
                className="rounded-lg bg-action px-3 py-2 text-sm text-on-action hover:opacity-90"
              >
                Sign in
              </Link>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">{children}</main>
    </div>
  )
}
