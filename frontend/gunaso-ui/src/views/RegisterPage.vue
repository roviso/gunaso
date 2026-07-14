<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import { useOnboardingStore } from '@/stores/onboarding'

const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUIStore()
const onboardingStore = useOnboardingStore()

const form = ref({
  name: '', email: '', password: '', confirmPassword: '',
  user_type: 'citizen'
})
const fieldErrors = ref({})
const showPassword = ref(false)
const nameInput = ref(null)

const accountTypes = [
  {
    value: 'citizen', label: 'Citizen', desc: 'Submit & track complaints',
    icon: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z'
  },
  {
    value: 'org_admin', label: 'Organization', desc: 'Receive & resolve submissions',
    icon: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4'
  },
]

// Lightweight strength heuristic for instant feedback (server enforces policy).
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

function validate() {
  fieldErrors.value = {}
  if (!form.value.name.trim()) fieldErrors.value.name = 'Full name is required.'
  if (!form.value.email.trim()) fieldErrors.value.email = 'Email is required.'
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.value.email)) fieldErrors.value.email = 'Enter a valid email.'
  if (!form.value.password) fieldErrors.value.password = 'Password is required.'
  else if (form.value.password.length < 8) fieldErrors.value.password = 'Password must be at least 8 characters.'
  if (form.value.password !== form.value.confirmPassword) fieldErrors.value.confirmPassword = 'Passwords do not match.'
  return Object.keys(fieldErrors.value).length === 0
}

async function handleSubmit() {
  if (!validate()) return
  authStore.error = null
  try {
    const { confirmPassword, ...payload } = form.value
    await authStore.register(payload)
    uiStore.showSuccess('Account created! Welcome to Gunaso.')
    router.push(onboardingStore.postAuthRoute(authStore.user))
  } catch {
    // errors shown from store
  }
}

onMounted(() => nameInput.value?.focus())
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
          Two minutes<br /><span class="text-primary-300">to be heard.</span>
        </p>
        <p class="text-blue-200/80 leading-relaxed mb-10 animate-fade-up" style="animation-delay: 0.1s">
          One free account to submit complaints, keep them all in one place, and
          watch organizations respond — step by step.
        </p>

        <ul class="space-y-4 animate-fade-up" style="animation-delay: 0.2s">
          <li v-for="(point, i) in [
            'Free forever — no fees, no ads',
            'Anonymous submissions never reveal your identity to organizations',
            'A permanent audit trail organizations cannot edit'
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
        <div class="card p-8">
          <div class="mb-7">
            <div class="w-12 h-12 bg-primary rounded-2xl flex items-center justify-center mb-5 shadow-lg shadow-primary/20">
              <span class="text-white font-display font-extrabold text-xl">G</span>
            </div>
            <h1 class="font-display text-2xl font-bold text-secondary dark:text-white">Create your account</h1>
            <p class="text-gray-500 dark:text-gray-400 text-sm mt-1">Join citizens across Nepal holding institutions accountable</p>
          </div>

          <!-- Account Type -->
          <fieldset class="mb-6">
            <legend class="label">I am a...</legend>
            <div class="grid grid-cols-2 gap-3">
              <button v-for="type in accountTypes" :key="type.value" type="button"
                @click="form.user_type = type.value"
                :aria-pressed="form.user_type === type.value"
                :class="['p-3.5 rounded-xl border-2 text-left transition-all duration-150',
                  form.user_type === type.value
                    ? 'border-primary bg-primary/5 dark:bg-primary/10'
                    : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500']">
                <span :class="['w-9 h-9 rounded-lg flex items-center justify-center mb-2',
                  form.user_type === type.value ? 'bg-primary/15 text-primary' : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400']">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" :d="type.icon"/>
                  </svg>
                </span>
                <p :class="['text-sm font-semibold', form.user_type === type.value ? 'text-primary' : 'text-gray-900 dark:text-white']">{{ type.label }}</p>
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{{ type.desc }}</p>
              </button>
            </div>
          </fieldset>

          <!-- Server errors -->
          <div v-if="authStore.error && typeof authStore.error === 'object'" role="alert" class="mb-5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-3.5">
            <p v-for="(msgs, field) in authStore.error" :key="field" class="text-sm text-red-700 dark:text-red-400">
              <span class="font-medium capitalize">{{ field }}:</span> {{ Array.isArray(msgs) ? msgs[0] : msgs }}
            </p>
          </div>
          <div v-else-if="authStore.error" role="alert" class="mb-5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-3.5">
            <p class="text-sm text-red-700 dark:text-red-400">{{ authStore.error }}</p>
          </div>

          <form @submit.prevent="handleSubmit" class="space-y-4" novalidate>
            <div>
              <label class="label" for="reg-name">Full name</label>
              <input id="reg-name" ref="nameInput" v-model="form.name" type="text" placeholder="Ram Prasad Sharma"
                :aria-invalid="!!fieldErrors.name"
                :class="['input-base', fieldErrors.name ? 'border-red-400' : '']" autocomplete="name" />
              <p v-if="fieldErrors.name" class="field-error">{{ fieldErrors.name }}</p>
            </div>

            <div>
              <label class="label" for="reg-email">Email address</label>
              <input id="reg-email" v-model="form.email" type="email" placeholder="you@example.com"
                :aria-invalid="!!fieldErrors.email"
                :class="['input-base', fieldErrors.email ? 'border-red-400' : '']" autocomplete="email" />
              <p v-if="fieldErrors.email" class="field-error">{{ fieldErrors.email }}</p>
            </div>

            <div>
              <label class="label" for="reg-password">Password</label>
              <div class="relative">
                <input id="reg-password" v-model="form.password" :type="showPassword ? 'text' : 'password'" placeholder="Minimum 8 characters"
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
              <label class="label" for="reg-confirm">Confirm password</label>
              <input id="reg-confirm" v-model="form.confirmPassword" :type="showPassword ? 'text' : 'password'" placeholder="Repeat password"
                :aria-invalid="!!fieldErrors.confirmPassword"
                :class="['input-base', fieldErrors.confirmPassword ? 'border-red-400' : '']" autocomplete="new-password" />
              <p v-if="fieldErrors.confirmPassword" class="field-error">{{ fieldErrors.confirmPassword }}</p>
            </div>

            <button type="submit" :disabled="authStore.loading" class="btn-primary w-full py-3.5 text-base mt-2">
              <svg v-if="authStore.loading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              {{ authStore.loading ? 'Creating account...' : 'Create Account' }}
            </button>
          </form>

          <p class="text-center text-sm text-gray-500 dark:text-gray-400 mt-6">
            Already have an account?
            <RouterLink to="/login" class="text-primary font-semibold hover:underline">Sign in</RouterLink>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
