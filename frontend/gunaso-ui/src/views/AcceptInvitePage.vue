<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { organizationsAPI } from '@/api/organizations'
import { apiErrorMessage } from '@/api/index'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUIStore()

const token = String(route.params.token || '')

// Preview state: the invite this token resolves to (organization, role, email).
const previewLoading = ref(true)
const invite = ref(null)
// True once we know the token is unusable — invalid, expired, or already
// accepted. The backend deliberately never distinguishes which (see
// apps/organizations/services.py::resolve_invite) so we show one calm
// terminal state rather than guessing at a reason.
const tokenUnusable = ref(false)

const form = ref({ password: '', confirmPassword: '' })
const fieldErrors = ref({})
const showPassword = ref(false)
const submitting = ref(false)
const submitError = ref(null)
const passwordInput = ref(null)

// Same lightweight strength heuristic as RegisterPage.vue for instant
// feedback (server enforces the real policy via StaffInviteAcceptSerializer).
const passwordStrength = computed(() => {
  const p = form.value.password
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

async function loadInvite() {
  previewLoading.value = true
  tokenUnusable.value = false
  invite.value = null

  if (!token) {
    tokenUnusable.value = true
    previewLoading.value = false
    return
  }

  try {
    const { data } = await organizationsAPI.previewInvite(token)
    invite.value = data
  } catch {
    // Preview 404s for every unusable-token reason on purpose (never
    // distinguishable) — one clear terminal state covers all of them.
    tokenUnusable.value = true
  } finally {
    previewLoading.value = false
  }
}

function validate() {
  fieldErrors.value = {}
  if (!form.value.password) fieldErrors.value.password = 'Password is required.'
  else if (form.value.password.length < 8) fieldErrors.value.password = 'Password must be at least 8 characters.'
  if (form.value.password !== form.value.confirmPassword) fieldErrors.value.confirmPassword = 'Passwords do not match.'
  return Object.keys(fieldErrors.value).length === 0
}

async function handleSubmit() {
  if (!validate()) return
  submitError.value = null
  submitting.value = true
  try {
    const { data } = await organizationsAPI.acceptInvite(token, { password: form.value.password })

    // Same session-setting mechanism authStore.login/register use — access
    // token in memory, user in localStorage — so the user lands authenticated
    // without a second login step.
    authStore.setSession(data)
    uiStore.showSuccess(`Welcome to ${invite.value?.organization || 'your organization'}!`)

    // A staff invitee's user_type stays 'citizen' (accept_invite never
    // changes it — see apps/organizations/services.py::accept_invite), and
    // onboardingStore.postAuthRoute() only special-cases user_type ===
    // 'org_admin' until it's broadened for staff access in subtask 10. Route
    // straight into the org dashboard so this flow isn't dead-ended today.
    router.push({ name: 'OrgDashboard' })
  } catch (err) {
    // Password-validation failures come back wrapped in the standard error
    // envelope (field_errors.password); a token that went stale between
    // preview and submit (expired/invalid/already used) comes back as a bare
    // {detail} response with no envelope — treat that as the same terminal
    // state the preview step shows, since retrying the form won't help.
    const isFieldValidation = !!err?.response?.data?.error
    if (!isFieldValidation && [400, 410].includes(err?.response?.status)) {
      invite.value = null
      tokenUnusable.value = true
    } else {
      submitError.value = apiErrorMessage(err, 'Could not set your password. Please try again.')
    }
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  await loadInvite()
  if (invite.value) passwordInput.value?.focus()
})
</script>

<template>
  <div class="min-h-[calc(100vh-4rem)] grid lg:grid-cols-2">
    <!-- ===== Brand panel ===== -->
    <div class="hidden lg:flex relative bg-gradient-to-br from-secondary via-[#16294a] to-secondary-900 text-white overflow-hidden">
      <div class="pointer-events-none absolute top-0 right-0 w-96 h-96 bg-primary/15 rounded-full -translate-y-1/3 translate-x-1/3 blur-3xl" />
      <div class="pointer-events-none absolute bottom-0 left-0 w-80 h-80 bg-accent/20 rounded-full translate-y-1/3 -translate-x-1/4 blur-3xl" />
      <div class="pointer-events-none absolute inset-0 opacity-[0.04]"
        style="background-image: radial-gradient(currentColor 1px, transparent 1px); background-size: 28px 28px;" />

      <div class="relative flex flex-col justify-center px-12 xl:px-20 py-16 max-w-xl">
        <p class="font-display text-4xl xl:text-5xl font-bold leading-tight tracking-tight mb-4 animate-fade-up">
          You've been<br /><span class="text-primary-300">invited to join.</span>
        </p>
        <p class="text-blue-200/80 leading-relaxed mb-10 animate-fade-up" style="animation-delay: 0.1s">
          Set a password to accept your invitation and start working alongside your
          organization's team on Gunaso.
        </p>

        <ul class="space-y-4 animate-fade-up" style="animation-delay: 0.2s">
          <li v-for="(point, i) in [
            'Your role and access are set by your organization admin',
            'One password, one click — no separate registration step',
            'This invite link can only be used once'
          ]" :key="i" class="flex items-start gap-3">
            <span class="w-5 h-5 rounded-full bg-green-400/20 border border-green-400/40 flex items-center justify-center shrink-0 mt-0.5">
              <svg class="w-3 h-3 text-green-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/>
              </svg>
            </span>
            <span class="text-sm text-blue-100/90 leading-relaxed">{{ point }}</span>
          </li>
        </ul>

        <p class="text-blue-300/60 text-sm italic mt-10 animate-fade-up" style="animation-delay: 0.3s">
          "आफ्नो आवाज उठाउनुस्" — Raise your voice.
        </p>
      </div>
    </div>

    <!-- ===== Form panel ===== -->
    <div class="flex items-center justify-center p-4 sm:p-8 py-10 bg-app-bg dark:bg-gray-900">
      <div class="w-full max-w-md animate-fade-up">

        <!-- Loading -->
        <div v-if="previewLoading" class="card p-8">
          <LoadingSpinner label="Checking your invite link..." />
        </div>

        <!-- Invalid / expired terminal state -->
        <div v-else-if="tokenUnusable" class="card p-8 text-center">
          <div class="w-14 h-14 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-5">
            <svg class="w-7 h-7 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
          <h1 class="font-display text-xl font-bold text-secondary dark:text-white mb-2">This invite link isn't valid</h1>
          <p class="text-gray-500 dark:text-gray-400 text-sm leading-relaxed mb-6">
            It may have expired, already been used, or been typed incorrectly.
            Ask your organization admin to resend the invite from their Staff page
            and open the fresh link they send you.
          </p>
          <div class="flex flex-col sm:flex-row gap-3 justify-center">
            <RouterLink to="/login" class="btn-primary">Go to Sign In</RouterLink>
            <RouterLink to="/" class="btn-secondary">Back to Home</RouterLink>
          </div>
        </div>

        <!-- Set-password form -->
        <div v-else-if="invite" class="card p-8">
          <div class="mb-7">
            <div class="w-12 h-12 bg-primary rounded-2xl flex items-center justify-center mb-5 shadow-lg shadow-primary/20">
              <span class="text-white font-display font-extrabold text-xl">G</span>
            </div>
            <h1 class="font-display text-2xl font-bold text-secondary dark:text-white">Accept your invite</h1>
            <p class="text-gray-500 dark:text-gray-400 text-sm mt-1">
              Set a password to join <span class="font-semibold text-secondary dark:text-white">{{ invite.organization }}</span>
            </p>
          </div>

          <!-- Invite summary -->
          <dl class="mb-6 bg-gray-50 dark:bg-gray-700/40 rounded-xl p-4 space-y-2.5 text-sm">
            <div class="flex items-center justify-between gap-3">
              <dt class="text-gray-500 dark:text-gray-400">Organization</dt>
              <dd class="font-semibold text-gray-900 dark:text-white text-right">{{ invite.organization }}</dd>
            </div>
            <div v-if="invite.role" class="flex items-center justify-between gap-3">
              <dt class="text-gray-500 dark:text-gray-400">Role</dt>
              <dd class="font-semibold text-gray-900 dark:text-white text-right">{{ invite.role }}</dd>
            </div>
            <div class="flex items-center justify-between gap-3">
              <dt class="text-gray-500 dark:text-gray-400">Email</dt>
              <dd class="font-semibold text-gray-900 dark:text-white text-right break-all">{{ invite.email }}</dd>
            </div>
          </dl>

          <!-- Submit errors -->
          <div v-if="submitError" role="alert" class="mb-5 flex items-start gap-2.5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-3.5">
            <svg class="w-4 h-4 text-red-600 dark:text-red-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
            <p class="text-sm text-red-700 dark:text-red-400">{{ submitError }}</p>
          </div>

          <form @submit.prevent="handleSubmit" class="space-y-4" novalidate>
            <div>
              <label class="label" for="invite-password">Password</label>
              <div class="relative">
                <input id="invite-password" ref="passwordInput" v-model="form.password" :type="showPassword ? 'text' : 'password'" placeholder="Minimum 8 characters"
                  :aria-invalid="!!fieldErrors.password"
                  :class="['input-base pr-10', fieldErrors.password ? 'border-red-400' : '']" autocomplete="new-password" />
                <button type="button" @click="showPassword = !showPassword"
                  :aria-label="showPassword ? 'Hide password' : 'Show password'"
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

              <!-- Strength meter -->
              <div v-if="form.password" class="mt-2">
                <div class="flex gap-1" aria-hidden="true">
                  <span v-for="i in 4" :key="i"
                    :class="['h-1 flex-1 rounded-full transition-colors duration-300',
                      i <= passwordStrength.score ? passwordStrength.color.split(' ')[0] : 'bg-gray-200 dark:bg-gray-700']" />
                </div>
                <p :class="['text-xs mt-1 font-medium', passwordStrength.color.split(' ').slice(1).join(' ')]">
                  {{ passwordStrength.label }}
                </p>
              </div>
              <p v-if="fieldErrors.password" class="field-error">{{ fieldErrors.password }}</p>
            </div>

            <div>
              <label class="label" for="invite-confirm">Confirm password</label>
              <input id="invite-confirm" v-model="form.confirmPassword" :type="showPassword ? 'text' : 'password'" placeholder="Repeat password"
                :aria-invalid="!!fieldErrors.confirmPassword"
                :class="['input-base', fieldErrors.confirmPassword ? 'border-red-400' : '']" autocomplete="new-password" />
              <p v-if="fieldErrors.confirmPassword" class="field-error">{{ fieldErrors.confirmPassword }}</p>
            </div>

            <button type="submit" :disabled="submitting" class="btn-primary w-full py-3.5 text-base mt-2">
              <svg v-if="submitting" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              {{ submitting ? 'Setting password...' : 'Accept Invite & Sign In' }}
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>
