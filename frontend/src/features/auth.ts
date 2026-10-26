import { api } from '../lib/http'
import type { User } from '../lib/types'

export async function register(email: string, password: string): Promise<User> {
  return api<User>('/auth/register', { method: 'POST', json: { email, password } })
}
