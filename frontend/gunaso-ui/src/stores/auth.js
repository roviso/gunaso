import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authAPI } from '@/api/auth'
import { apiErrorMessage, refreshSession, setAccessToken } from '@/api/index'

const USER_KEY = 'gunaso_user'

function readStoredUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null')
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  // Only the (non-sensitive) profile is persisted; tokens never touch storage.
  const user = ref(readStoredUser())
  const loading = ref(false)
  const error = ref(null)
  const initialized = ref(false)

  const isAuthenticated = computed(() => !!user.value)
  const isCitizen = computed(() => user.value?.user_type === 'citizen')
  const isOrgAdmin = computed(() => user.value?.user_type === 'org_admin')
  const userInitial = computed(() => user.value?.name?.[0]?.toUpperCase() || 'U')

  function setSession(data) {
    setAccessToken(data.access)
    user.value = data.user
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
  }

  function clearSession() {
    setAccessToken(null)
    user.value = null
    localStorage.removeItem(USER_KEY)
  }

  /** Restore the session from the httpOnly refresh cookie on app start. */
  async function init() {
    if (initialized.value) return
    initialized.value = true
    window.addEventListener('gunaso:session-expired', clearSession)
    if (!user.value) return
    try {
      const data = await refreshSession()
      if (data.user) {
        user.value = data.user
        localStorage.setItem(USER_KEY, JSON.stringify(data.user))
      }
    } catch {
      clearSession()
    }
  }

  async function login(credentials) {
    loading.value = true
    error.value = null
    try {
      const { data } = await authAPI.login(credentials)
      setSession(data)
      return data
    } catch (err) {
      error.value = apiErrorMessage(err, 'Invalid email or password.')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function register(userData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await authAPI.register(userData)
      setSession(data)
      return data
    } catch (err) {
      error.value = apiErrorMessage(err, 'Registration failed. Please try again.')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchMe() {
    if (!user.value) return
    try {
      const { data } = await authAPI.me()
      user.value = data
      localStorage.setItem(USER_KEY, JSON.stringify(data))
    } catch {
      // Interceptor already attempted a refresh; a failure here means the
      // session is gone.
      clearSession()
    }
  }

  async function logout() {
    try {
      await authAPI.logout()
    } catch {
      // Even if the server call fails, drop the local session.
    }
    clearSession()
  }

  return {
    user, loading, error,
    isAuthenticated, isCitizen, isOrgAdmin, userInitial,
    init, login, register, fetchMe, logout
  }
})
