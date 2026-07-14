import { defineStore } from 'pinia'
import { ref } from 'vue'

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

  /** Where to send a user right after authentication. */
  function postAuthRoute(user) {
    if (user?.id && !hasOnboarded(user.id)) return { name: 'Welcome' }
    return user?.user_type === 'org_admin' ? { name: 'OrgDashboard' } : { name: 'Dashboard' }
  }

  return { completed, hasOnboarded, markOnboarded, postAuthRoute }
})
