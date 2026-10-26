import { BrowserRouter } from 'react-router-dom'
import { Shell } from '../components/Shell'
import { AppQueryProvider } from './query'
import { AppRoutes } from './routes'
import { SessionProvider } from './session'
import { ThemeProvider } from './theme'

export function App() {
  return (
    <ThemeProvider>
      <AppQueryProvider>
        <SessionProvider>
          <BrowserRouter>
            <Shell>
              <AppRoutes />
            </Shell>
          </BrowserRouter>
        </SessionProvider>
      </AppQueryProvider>
    </ThemeProvider>
  )
}
