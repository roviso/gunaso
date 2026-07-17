import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

// Onboarding completion is a per-device UX flag, not account data —
// keyed by user id so shared devices don't skip a new user's welcome.
const KEY = 'gunaso_onboarded'

function readCompleted() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '{}')
  } catch {
    return {}
  }
}

export const useOnboardingStore = defineStore('onboarding', () => {
  const completed = ref(readCompleted())

  function hasOnboarded(userId) {
    return !!completed.value[userId]
  }

  function markOnboarded(userId) {
    if (!userId) return
    completed.value = { ...completed.value, [userId]: true }
    localStorage.setItem(KEY, JSON.stringify(completed.value))
  }

  /**
   * Where to send a user right after authentication. Async: a non-org_admin
   * user's org access (active staff role/privileges) isn't knowable from the
   * `user` object alone — it's a separate lookup (see
   * authStore.fetchStaffAccess / apps/organizations/views.py::MyStaffAccessView)
   * that must resolve first. Without this, a staff invitee — whose user_type
   * stays 'citizen' since accepting an invite never changes it — was always
   * misrouted to the citizen dashboard instead of /org/dashboard.
   */
  async function postAuthRoute(user) {
    // Superadmins skip the citizen/org onboarding flow entirely — the
    // control room is their home, not the welcome wizard.
    if (user?.is_superuser) return { name: 'AdminOverview' }
    if (user?.id && !hasOnboarded(user.id)) return { name: 'Welcome' }
    if (user?.user_type === 'org_admin') return { name: 'OrgDashboard' }

    const authStore = useAuthStore()
    if (!authStore.staffAccess.organization_slug && !authStore.staffAccessLoading) {
      await authStore.fetchStaffAccess()
    }
    return authStore.hasOrgAccess ? { name: 'OrgDashboard' } : { name: 'Dashboard' }
  }

  return { completed, hasOnboarded, markOnboarded, postAuthRoute }
})
