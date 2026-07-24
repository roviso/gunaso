import { defineStore } from 'pinia'
import { useAuthStore } from '@/stores/auth'

// Legacy per-device completion flag, superseded by the account-level
// User.has_completed_onboarding field. Kept read-only here only to backfill
// accounts that finished onboarding under the old scheme (on this device)
// before that field existed, so they aren't sent through the wizard again
// after upgrading.
const LEGACY_KEY = 'gunaso_onboarded'

function readLegacyCompleted() {
  try {
    return JSON.parse(localStorage.getItem(LEGACY_KEY) || '{}')
  } catch {
    return {}
  }
}

export const useOnboardingStore = defineStore('onboarding', () => {
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

    if (user?.id && !user.has_completed_onboarding) {
      if (readLegacyCompleted()[user.id]) {
        // Already finished onboarding on this device under the old scheme —
        // sync it to the account so it's recognized everywhere from now on,
        // and don't show the wizard again.
        useAuthStore().markOnboardingComplete().catch(() => {})
      } else {
        return { name: 'Welcome' }
      }
    }

    if (user?.user_type === 'org_admin') return { name: 'OrgDashboard' }

    const authStore = useAuthStore()
    if (!authStore.staffAccess.organization_slug && !authStore.staffAccessLoading) {
      await authStore.fetchStaffAccess()
    }
    return authStore.hasOrgAccess ? { name: 'OrgDashboard' } : { name: 'Dashboard' }
  }

  return { postAuthRoute }
})
