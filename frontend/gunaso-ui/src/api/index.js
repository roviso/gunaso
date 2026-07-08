import axios from 'axios'

// The access token lives in memory only (never localStorage) to reduce XSS
// exposure. The refresh token lives in an httpOnly cookie set by the backend.
let accessToken = null

export function setAccessToken(token) {
  accessToken = token
}

export function getAccessToken() {
  return accessToken
}

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const api = axios.create({
  baseURL,
  timeout: 15000,
  withCredentials: true
})

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  return config
})

// Single-flight refresh: concurrent 401s share one refresh request.
let refreshPromise = null

async function refreshSession() {
  if (!refreshPromise) {
    refreshPromise = axios
      .post(`${baseURL}/auth/refresh/`, {}, { withCredentials: true })
      .then(({ data }) => {
        setAccessToken(data.access)
        return data
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

const AUTH_PATHS = ['/auth/login/', '/auth/register/', '/auth/refresh/', '/auth/logout/']

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error
    const isAuthCall = AUTH_PATHS.some((p) => config?.url?.includes(p))

    if (response?.status === 401 && !config._retried && !isAuthCall) {
      config._retried = true
      try {
        await refreshSession()
        return api(config)
      } catch {
        setAccessToken(null)
        window.dispatchEvent(new CustomEvent('gunaso:session-expired'))
      }
    }
    return Promise.reject(error)
  }
)

/** Extract a human-readable message from the API error envelope. */
export function apiErrorMessage(err, fallback = 'Something went wrong. Please try again.') {
  const envelope = err?.response?.data?.error
  if (envelope) {
    const fieldErrors = envelope.field_errors || {}
    const firstField = Object.keys(fieldErrors)[0]
    if (firstField) {
      const value = fieldErrors[firstField]
      return Array.isArray(value) ? String(value[0]) : String(value)
    }
    if (envelope.message) return envelope.message
  }
  return err?.response?.data?.detail || fallback
}

export { refreshSession }
export default api
