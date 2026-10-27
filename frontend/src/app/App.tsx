import { BrowserRouter } from 'react-router-dom'
import { Shell } from '../components/Shell'
import { AppQueryProvider } from './query'
import { AppRoutes } from './routes'
import { SessionProvider } from './session'
import { ThemeProvider } from './theme'
import { ToastProvider } from './toast'

export function App() {
  return (
    <ThemeProvider>
      <AppQueryProvider>
        <SessionProvider>
          <BrowserRouter>
            <ToastProvider>
              <Shell>
                <AppRoutes />
              </Shell>
            </ToastProvider>
          </BrowserRouter>
        </SessionProvider>
      </AppQueryProvider>
    </ThemeProvider>
  )
}
