import { Link, useNavigate } from 'react-router-dom'
import { useSession } from '../app/session'
import { useTheme } from '../app/theme'
import { Button } from './Button'

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

const navLink = 'text-sm font-semibold text-text hover:text-brand'

export function Shell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useSession()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex h-[88px] max-w-[1312px] items-center justify-between gap-4 px-6 md:px-16">
          <nav className="flex flex-wrap items-center gap-6 md:gap-8">
            <Link
              to="/"
              className="text-base font-semibold lowercase tracking-tight text-brand hover:opacity-90"
            >
              hammerz
            </Link>
            <Link to="/" className={navLink}>Auctions</Link>
            {user?.role === 'BIDDER' && (
              <>
                <Link to="/my-wins" className={navLink}>My Bids &amp; Wins</Link>
                <Link to="/wallet" className={navLink}>Wallet</Link>
              </>
            )}
            {user?.role === 'SELLER' && (
              <Link to="/seller" className={navLink}>Seller dashboard</Link>
            )}
          </nav>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            {user ? (
              <Button
                variant="secondary"
                className="h-10 px-4"
                onClick={() => {
                  logout()
                  navigate('/')
                }}
              >
                Sign out
              </Button>
            ) : (
              <Link
                to="/login"
                className="inline-flex h-10 items-center justify-center rounded-lg border border-border bg-surface px-4 text-sm font-semibold text-brand hover:bg-brand-soft"
              >
                Sign in
              </Link>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[1312px] px-6 py-10 md:px-16">{children}</main>
    </div>
  )
}
