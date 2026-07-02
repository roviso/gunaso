import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authAPI } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(JSON.parse(localStorage.getItem('gunaso_user') || 'null'))
  const token = ref(localStorage.getItem('gunaso_token') || null)
  const loading = ref(false)
  const error = ref(null)

  const isAuthenticated = computed(() => !!token.value)
  const isCitizen = computed(() => user.value?.user_type === 'citizen' || (user.value && !user.value?.user_type))
  const isOrgAdmin = computed(() => user.value?.user_type === 'org_admin')
  const userInitial = computed(() => user.value?.name?.[0]?.toUpperCase() || 'U')

  async function login(credentials) {
    loading.value = true
    error.value = null
    try {
      const { data } = await authAPI.login(credentials)
      token.value = data.access
      user.value = data.user
      localStorage.setItem('gunaso_token', data.access)
      localStorage.setItem('gunaso_user', JSON.stringify(data.user))
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.response?.data?.non_field_errors?.[0] || 'Invalid email or password.'
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
      token.value = data.access
      user.value = data.user
      localStorage.setItem('gunaso_token', data.access)
      localStorage.setItem('gunaso_user', JSON.stringify(data.user))
      return data
    } catch (err) {
      error.value = err.response?.data || { detail: 'Registration failed. Please try again.' }
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchMe() {
    if (!token.value) return
    try {
      const { data } = await authAPI.me()
      user.value = data
      localStorage.setItem('gunaso_user', JSON.stringify(data))
    } catch {
      logout()
    }
  }

  function logout() {
    user.value = null
    token.value = null
    localStorage.removeItem('gunaso_token')
    localStorage.removeItem('gunaso_user')
  }

  return {
    user, token, loading, error,
    isAuthenticated, isCitizen, isOrgAdmin, userInitial,
    login, register, fetchMe, logout
  }
})
