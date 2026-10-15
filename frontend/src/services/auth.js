import api from '@/api'
import { setSession, clearSession } from '@/store/session'

export async function login(email, password) {
  const res = await api.post('/api/auth/login', { email, password })
  setSession(res.data.token, res.data.user)
  return res.data.user
}

export async function logout() {
  try {
    await api.post('/api/auth/logout')
  } catch (e) {
    /* token may already be invalid */
  }
  clearSession()
}
