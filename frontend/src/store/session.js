import { reactive } from 'vue'

const KEY = 'placement_portal_session'

function load() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || {}
  } catch (e) {
    return {}
  }
}

const saved = load()

// Reactive auth state shared by the router, API client and components
export const session = reactive({ token: saved.token || null, user: saved.user || null })

function persist() {
  try {
    if (session.token) {
      localStorage.setItem(KEY, JSON.stringify({ token: session.token, user: session.user }))
    } else {
      localStorage.removeItem(KEY)
    }
  } catch (e) {
    /* storage unavailable: keep the in-memory session only */
  }
}

export function setSession(token, user) {
  session.token = token
  session.user = user
  persist()
}

export function clearSession() {
  session.token = null
  session.user = null
  persist()
}

export const homeFor = (role) => ({ admin: '/admin', company: '/company', student: '/student' }[role] || '/login')
