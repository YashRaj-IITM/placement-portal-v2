import axios from 'axios'
import { session, clearSession } from '@/store/session'

const api = axios.create({ baseURL: process.env.VUE_APP_API_URL || '' })

// Attach the access token issued by Flask-Security to every request
api.interceptors.request.use((config) => {
  if (session.token) config.headers['Authentication-Token'] = session.token
  return config
})

// Expired / invalid token: clear the session and go back to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = (error.config && error.config.url) || ''
    if (error.response && error.response.status === 401 && !url.includes('/auth/login')) {
      clearSession()
      if (!window.location.pathname.startsWith('/login')) window.location.assign('/login')
    }
    return Promise.reject(error)
  }
)

export function errMsg(error, fallback = 'Something went wrong') {
  return (error.response && error.response.data && error.response.data.message) || fallback
}

export default api
