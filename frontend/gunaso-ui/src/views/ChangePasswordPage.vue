<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import { apiErrorMessage } from '@/api/index'

const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUIStore()

const form = ref({ current_password: '', new_password: '', confirmPassword: '' })
const fieldErrors = ref({})
const submitError = ref(null)
const submitting = ref(false)
const showPassword = ref(false)

const passwordStrength = computed(() => {
  const p = form.value.new_password
  if (!p) return { score: 0, label: '', color: '' }
  let score = 0
  if (p.length >= 8) score++
  if (p.length >= 12) score++
  if (/[A-Z]/.test(p) && /[a-z]/.test(p)) score++
  if (/\d/.test(p) || /[^A-Za-z0-9]/.test(p)) score++
  const levels = [
    { label: 'Too short', color: 'bg-red-400 text-red-600 dark:text-red-400' },
    { label: 'Weak', color: 'bg-orange-400 text-orange-600 dark:text-orange-400' },
    { label: 'Okay', color: 'bg-amber-400 text-amber-600 dark:text-amber-400' },
    { label: 'Good', color: 'bg-lime-500 text-lime-600 dark:text-lime-400' },
    { label: 'Strong', color: 'bg-green-500 text-green-600 dark:text-green-400' },
  ]
  return { score, ...levels[score] }
})

function validate() {
  fieldErrors.value = {}
  if (!form.value.current_password) fieldErrors.value.current_password = 'Enter your current password.'
  if (!form.value.new_password) fieldErrors.value.new_password = 'Password is required.'
  else if (form.value.new_password.length < 8) fieldErrors.value.new_password = 'Password must be at least 8 characters.'
  if (form.value.new_password !== form.value.confirmPassword) fieldErrors.value.confirmPassword = 'Passwords do not match.'
  return Object.keys(fieldErrors.value).length === 0
}

async function handleSubmit() {
  if (!validate()) return
  submitError.value = null
  submitting.value = true
  try {
    await authStore.changePassword({
      current_password: form.value.current_password,
      new_password: form.value.new_password,
    })
    uiStore.showSuccess('Password updated.')
    await authStore.fetchStaffAccess()
    router.replace(authStore.hasOrgAccess ? { name: 'OrgDashboard' } : { name: 'Dashboard' })
  } catch (err) {
    const errors = err?.response?.data?.error?.field_errors
    if (errors?.current_password) fieldErrors.value.current_password = errors.current_password[0]
    if (errors?.new_password) fieldErrors.value.new_password = errors.new_password[0]
    if (!errors) submitError.value = apiErrorMessage(err, 'Could not update your password. Please try again.')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-4 sm:p-8 bg-app-bg dark:bg-gray-900">
    <div class="w-full max-w-md animate-fade-up">
      <div class="card p-8">
        <div class="mb-7">
          <div class="w-12 h-12 bg-primary rounded-2xl flex items-center justify-center mb-5 shadow-lg shadow-primary/20">
            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
            </svg>
          </div>
          <h1 class="font-display text-2xl font-bold text-secondary dark:text-white">Set a new password</h1>
          <p class="text-gray-500 dark:text-gray-400 text-sm mt-1">
            Your organization admin set up this account for you — pick a password only you know before continuing.
          </p>
        </div>

        <div v-if="submitError" role="alert" class="mb-5 flex items-start gap-2.5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-3.5">
          <svg class="w-4 h-4 text-red-600 dark:text-red-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
          </svg>
          <p class="text-sm text-red-700 dark:text-red-400">{{ submitError }}</p>
        </div>

        <form @submit.prevent="handleSubmit" class="space-y-4" novalidate>
          <div>
            <label class="label" for="current-password">Current (temporary) password</label>
            <input id="current-password" v-model="form.current_password" :type="showPassword ? 'text' : 'password'"
              :aria-invalid="!!fieldErrors.current_password"
              :class="['input-base', fieldErrors.current_password ? 'border-red-400' : '']" autocomplete="current-password" />
            <p v-if="fieldErrors.current_password" class="field-error">{{ fieldErrors.current_password }}</p>
          </div>

          <div>
            <label class="label" for="new-password">New password</label>
            <div class="relative">
              <input id="new-password" v-model="form.new_password" :type="showPassword ? 'text' : 'password'" placeholder="Minimum 8 characters"
                :aria-invalid="!!fieldErrors.new_password"
                :class="['input-base pr-10', fieldErrors.new_password ? 'border-red-400' : '']" autocomplete="new-password" />
              <button type="button" @click="showPassword = !showPassword"
                :aria-label="showPassword ? 'Hide passwords' : 'Show passwords'"
                class="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                <svg v-if="!showPassword" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                </svg>
                <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
                </svg>
              </button>
            </div>
            <div v-if="form.new_password" class="mt-2">
              <div class="flex gap-1" aria-hidden="true">
                <span v-for="i in 4" :key="i"
                  :class="['h-1 flex-1 rounded-full transition-colors duration-300',
                    i <= passwordStrength.score ? passwordStrength.color.split(' ')[0] : 'bg-gray-200 dark:bg-gray-700']" />
              </div>
              <p :class="['text-xs mt-1 font-medium', passwordStrength.color.split(' ').slice(1).join(' ')]">
                {{ passwordStrength.label }}
              </p>
            </div>
            <p v-if="fieldErrors.new_password" class="field-error">{{ fieldErrors.new_password }}</p>
          </div>

          <div>
            <label class="label" for="confirm-password">Confirm new password</label>
            <input id="confirm-password" v-model="form.confirmPassword" :type="showPassword ? 'text' : 'password'"
              :aria-invalid="!!fieldErrors.confirmPassword"
              :class="['input-base', fieldErrors.confirmPassword ? 'border-red-400' : '']" autocomplete="new-password" />
            <p v-if="fieldErrors.confirmPassword" class="field-error">{{ fieldErrors.confirmPassword }}</p>
          </div>

          <button type="submit" :disabled="submitting" class="btn-primary w-full py-3.5 text-base mt-2">
            <svg v-if="submitting" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            {{ submitting ? 'Updating...' : 'Set Password & Continue' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>
