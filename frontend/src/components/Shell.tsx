import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
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
      className="flex h-10 w-10 items-center justify-center rounded-lg text-muted transition-colors hover:text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
    >
      {pressed ? (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.5" />
          <path
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"
          />
        </svg>
      ) : (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M21 14.5A8.5 8.5 0 0 1 9.5 3 7 7 0 1 0 21 14.5Z"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
        </svg>
      )}
    </button>
  )
}

const shellInset = 'mx-auto w-full max-w-[1440px] px-6 md:px-16'

function navItemClass(active: boolean): string {
  const base =
    'relative flex items-center self-stretch px-0.5 text-sm transition-colors after:pointer-events-none'
  if (active) {
    return `${base} font-semibold text-brand after:absolute after:inset-x-0 after:bottom-0 after:h-[2px] after:rounded-full after:bg-brand`
  }
  return `${base} font-normal text-muted hover:text-brand`
}

function auctionsActive(pathname: string): boolean {
  return pathname === '/' || pathname.startsWith('/lots/')
}

export function Shell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useSession()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const auctionsIsCurrent = auctionsActive(pathname)

  return (
    <div className="min-h-screen bg-bg bg-dots">
      <header className={`${shellInset} pt-5 md:pt-6`}>
        <div
          className="flex h-[60px] items-stretch justify-between gap-4 rounded-2xl border border-border bg-surface/90 px-5 backdrop-blur-sm md:px-8"
        >
          <div className="flex min-w-0 items-stretch gap-8 md:gap-14">
            <Link
              to="/"
              className="flex shrink-0 items-center font-display text-[28px] font-normal leading-none text-text hover:opacity-90"
            >
              hammerz
            </Link>
            <nav className="flex min-w-0 items-stretch gap-6 md:gap-8">
              <Link to="/" className={navItemClass(auctionsIsCurrent)}>
                Auctions
              </Link>
              {user?.role === 'BIDDER' && (
                <>
                  <NavLink to="/my-wins" className={({ isActive }) => navItemClass(isActive)}>
                    My Bids &amp; Wins
                  </NavLink>
                  <NavLink to="/wallet" className={({ isActive }) => navItemClass(isActive)}>
                    Wallet
                  </NavLink>
                </>
              )}
              {user?.role === 'SELLER' && (
                <NavLink to="/seller" className={({ isActive }) => navItemClass(isActive)}>
                  Seller dashboard
                </NavLink>
              )}
            </nav>
          </div>
          <div className="flex shrink-0 items-center gap-2 md:gap-3">
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
                className="inline-flex h-10 min-w-[112px] items-center justify-center rounded-lg bg-brand px-5 text-sm font-semibold text-bg transition-opacity hover:opacity-90"
              >
                Sign in
              </Link>
            )}
          </div>
        </div>
      </header>
      <main className={`${shellInset} py-10`}>{children}</main>
    </div>
  )
}
