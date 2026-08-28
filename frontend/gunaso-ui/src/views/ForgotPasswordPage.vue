<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { apiErrorMessage } from '@/api/index'

const authStore = useAuthStore()

const email = ref('')
const fieldErrors = ref({})
const submitError = ref(null)
const submitting = ref(false)
// The backend answers identically for a known and an unknown address, so the
// success screen must stay generic — saying "we sent it" only for real
// accounts would leak exactly what the endpoint refuses to.
const sent = ref(false)
const emailInput = ref(null)

function validate() {
  fieldErrors.value = {}
  if (!email.value.trim()) fieldErrors.value.email = 'Email is required.'
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) fieldErrors.value.email = 'Enter a valid email address.'
  return Object.keys(fieldErrors.value).length === 0
}

async function handleSubmit() {
  if (!validate()) return
  submitError.value = null
  submitting.value = true
  try {
    await authStore.requestPasswordReset(email.value.trim())
    sent.value = true
  } catch (err) {
    const errors = err?.response?.data?.error?.field_errors
    if (errors?.email) fieldErrors.value.email = errors.email[0]
    else submitError.value = apiErrorMessage(err, 'Could not send the reset link. Please try again.')
  } finally {
    submitting.value = false
  }
}

function tryAgain() {
  sent.value = false
  submitError.value = null
}

onMounted(() => emailInput.value?.focus())
</script>

<template>
  <div class="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4 sm:p-8 bg-app-bg dark:bg-gray-900">
    <div class="w-full max-w-md animate-fade-up">
      <!-- ===== Sent confirmation ===== -->
      <div v-if="sent" class="card p-8 text-center">
        <div class="w-14 h-14 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-5">
          <svg class="w-7 h-7 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
          </svg>
        </div>
        <h1 class="font-display text-xl font-bold text-secondary dark:text-white mb-2">Check your inbox</h1>
        <p class="text-gray-500 dark:text-gray-400 text-sm leading-relaxed mb-2">
          If an account exists for <span class="font-semibold text-gray-700 dark:text-gray-200">{{ email }}</span>,
          we've sent it a link to set a new password.
        </p>
        <p class="text-gray-400 dark:text-gray-500 text-xs leading-relaxed mb-6">
          The link expires in 24 hours. Nothing yet? Check your spam folder before trying again.
        </p>
        <div class="flex flex-col sm:flex-row gap-2.5 justify-center">
          <RouterLink to="/login" class="btn-primary">Back to Sign In</RouterLink>
          <button type="button" @click="tryAgain" class="btn-secondary">Use a different email</button>
        </div>
      </div>

      <!-- ===== Request form ===== -->
      <div v-else class="card p-8">
        <div class="mb-7">
          <div class="w-12 h-12 bg-primary rounded-2xl flex items-center justify-center mb-5 shadow-lg shadow-primary/20">
            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/>
            </svg>
          </div>
          <h1 class="font-display text-2xl font-bold text-secondary dark:text-white">Forgot your password?</h1>
          <p class="text-gray-500 dark:text-gray-400 text-sm mt-1">
            Enter the email address on your account and we'll send you a link to set a new password.
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
            <label class="label" for="reset-email">Email address</label>
            <input id="reset-email" ref="emailInput" v-model="email" type="email" placeholder="you@example.com"
              :aria-invalid="!!fieldErrors.email"
              :class="['input-base', fieldErrors.email ? 'border-red-400 focus:border-red-400 focus:ring-red-200' : '']"
              autocomplete="email" />
            <p v-if="fieldErrors.email" class="field-error">{{ fieldErrors.email }}</p>
          </div>

          <button type="submit" :disabled="submitting" class="btn-primary w-full py-3.5 text-base mt-2">
            <svg v-if="submitting" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            {{ submitting ? 'Sending...' : 'Send Reset Link' }}
          </button>
        </form>

        <p class="text-center text-sm text-gray-500 dark:text-gray-400 mt-6">
          Remembered it?
          <RouterLink to="/login" class="text-primary font-semibold hover:underline">Sign in</RouterLink>
        </p>
      </div>
    </div>
  </div>
</template>
