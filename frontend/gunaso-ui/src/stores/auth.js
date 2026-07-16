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

  // The current user's *active* OrganizationStaff membership (organization,
  // role name, privileges) — separate from `user.organization_slug`, which
  // only answers "does this user manage an org as org_admin?" (see
  // apps/organizations/views.py::MyStaffAccessView). Defaults mirror the
  // backend's "no access" shape so consumers never need to null-check twice.
  const staffAccess = ref({ organization_name: null, organization_slug: null, role_name: null, privileges: [] })
  const staffAccessLoading = ref(false)
  const staffAccessError = ref(null)

  const isAuthenticated = computed(() => !!user.value)
  const isCitizen = computed(() => user.value?.user_type === 'citizen')
  const isOrgAdmin = computed(() => user.value?.user_type === 'org_admin')
  const userInitial = computed(() => user.value?.name?.[0]?.toUpperCase() || 'U')

  // True for an admin-created staff account that hasn't set its own password
  // yet (User.must_change_password) — the router forces a change-password
  // screen before anything else while this is true.
  const mustChangePassword = computed(() => !!user.value?.must_change_password)
  const emailVerified = computed(() => user.value?.email_verified !== false)

  // True when the user manages an org (org_admin) or holds an active staff
  // membership somewhere — the general "can this user reach /org/* at all"
  // check for router guards. Per-page/per-action gating still needs hasPrivilege.
  const hasOrgAccess = computed(() => isOrgAdmin.value || !!staffAccess.value?.organization_slug)

  // The org slug the user currently has org-side access to, whichever
  // relationship (org_admin or active staff) supplies it.
  const accessibleOrgSlug = computed(() => user.value?.organization_slug || staffAccess.value?.organization_slug || null)

  function setSession(data) {
    setAccessToken(data.access)
    user.value = data.user
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    // Fire-and-forget: hasOrgAccess must be correct immediately after login
    // for non-admin staff (navbar links, router redirects, onboarding) —
    // waiting until they happen to visit /org/* first left it false too long.
    // Not awaited so a slow request never blocks the login/register flow.
    if (data.user?.user_type !== 'org_admin') fetchStaffAccess()
  }

  function clearSession() {
    setAccessToken(null)
    user.value = null
    localStorage.removeItem(USER_KEY)
    staffAccess.value = { organization_name: null, organization_slug: null, role_name: null, privileges: [] }
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
        if (data.user.user_type !== 'org_admin') fetchStaffAccess()
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

  /** Fetch the current user's active org-staff role & privileges (subtask 05 endpoint). */
  async function fetchStaffAccess() {
    if (!user.value) return
    staffAccessLoading.value = true
    staffAccessError.value = null
    try {
      const { data } = await authAPI.getMyOrgAccess()
      staffAccess.value = data
      return data
    } catch (err) {
      staffAccessError.value = apiErrorMessage(err, 'Could not load your staff access.')
    } finally {
      staffAccessLoading.value = false
    }
  }

  /**
   * Does the current user hold `privilege` for `orgSlug` (defaults to
   * whichever org they're currently accessible in)? Org admins implicitly
   * hold every privilege for the org they manage, mirroring
   * HasOrgPrivilege's server-side behaviour (org.admin bypasses the
   * privilege list entirely) — see apps/organizations/permissions.py.
   */
  function hasPrivilege(privilege, orgSlug = null) {
    const targetSlug = orgSlug || accessibleOrgSlug.value
    if (!targetSlug) return false
    if (isOrgAdmin.value && user.value?.organization_slug === targetSlug) return true
    if (staffAccess.value?.organization_slug === targetSlug) {
      return (staffAccess.value.privileges || []).includes(privilege)
    }
    return false
  }

  async function changePassword(payload) {
    const { data } = await authAPI.changePassword(payload)
    user.value = data.user
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    return data.user
  }

  async function requestEmailVerification(payload = {}) {
    const { data } = await authAPI.requestEmailVerification(payload)
    if (data.email && data.email !== user.value?.email) {
      user.value = { ...user.value, email: data.email }
      localStorage.setItem(USER_KEY, JSON.stringify(user.value))
    }
    return data
  }

  async function confirmEmailVerification(token) {
    const { data } = await authAPI.confirmEmailVerification(token)
    if (user.value) {
      user.value = { ...user.value, email_verified: true }
      localStorage.setItem(USER_KEY, JSON.stringify(user.value))
    }
    return data
  }

  return {
    user, loading, error,
    staffAccess, staffAccessLoading, staffAccessError,
    isAuthenticated, isCitizen, isOrgAdmin, userInitial,
    hasOrgAccess, accessibleOrgSlug, mustChangePassword, emailVerified,
    init, login, register, fetchMe, logout,
    fetchStaffAccess, hasPrivilege,
    changePassword, requestEmailVerification, confirmEmailVerification,
    // Exposed so flows that authenticate outside login/register — e.g.
    // AcceptInvitePage.vue's set-password step — can land the user in an
    // authenticated session via the exact same mechanism (access token in
    // memory, user in localStorage) without a second login round-trip.
    setSession,
  }
})
