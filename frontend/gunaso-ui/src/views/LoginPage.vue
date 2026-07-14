<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import { useOnboardingStore } from '@/stores/onboarding'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const uiStore = useUIStore()
const onboardingStore = useOnboardingStore()

const form = ref({ email: '', password: '' })
const showPassword = ref(false)
const fieldErrors = ref({})
const emailInput = ref(null)

const lifecycle = [
  { label: 'Submitted', color: 'bg-amber-400' },
  { label: 'Acknowledged', color: 'bg-cyan-400' },
  { label: 'In Review', color: 'bg-blue-400' },
  { label: 'Resolved', color: 'bg-green-400' },
]

function validate() {
  fieldErrors.value = {}
  if (!form.value.email.trim()) fieldErrors.value.email = 'Email is required.'
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.value.email)) fieldErrors.value.email = 'Enter a valid email address.'
  if (!form.value.password) fieldErrors.value.password = 'Password is required.'
  return Object.keys(fieldErrors.value).length === 0
}

async function handleSubmit() {
  if (!validate()) return
  authStore.error = null
  try {
    await authStore.login(form.value)
    uiStore.showSuccess('Welcome back!')
    const redirect = route.query.redirect
    if (redirect) router.push(String(redirect))
    else router.push(onboardingStore.postAuthRoute(authStore.user))
  } catch {
    // error is set in the store
  }
}

onMounted(() => emailInput.value?.focus())
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
          Your voice,<br /><span class="text-primary-300">on the record.</span>
        </p>
        <p class="text-blue-200/80 leading-relaxed mb-10 animate-fade-up" style="animation-delay: 0.1s">
          Track every complaint through a transparent, tamper-proof timeline —
          from submission to resolution.
        </p>

        <div class="rounded-2xl bg-white/[0.05] border border-white/10 p-5 animate-fade-up" style="animation-delay: 0.2s">
          <p class="text-xs uppercase tracking-widest text-blue-300/70 font-semibold mb-4">The Gunaso timeline</p>
          <div class="flex items-center justify-between">
            <template v-for="(stage, i) in lifecycle" :key="stage.label">
              <div class="flex flex-col items-center gap-2">
                <span :class="['w-2.5 h-2.5 rounded-full', stage.color, i === 0 ? 'animate-pulse-dot' : '']" />
                <span class="text-[11px] text-blue-100/90 font-medium whitespace-nowrap">{{ stage.label }}</span>
              </div>
              <div v-if="i < lifecycle.length - 1" class="flex-1 h-px bg-white/15 mx-2" />
            </template>
          </div>
        </div>

        <p class="text-blue-300/60 text-sm italic mt-10 animate-fade-up" style="animation-delay: 0.3s">
          "आफ्नो आवाज उठाउनुस्" — Raise your voice.
        </p>
      </div>
    </div>

    <!-- ===== Form panel ===== -->
    <div class="flex items-center justify-center p-4 sm:p-8 bg-app-bg dark:bg-gray-900">
      <div class="w-full max-w-md animate-fade-up">
        <div class="card p-8">
          <div class="mb-8">
            <div class="w-12 h-12 bg-primary rounded-2xl flex items-center justify-center mb-5 shadow-lg shadow-primary/20">
              <span class="text-white font-display font-extrabold text-xl">G</span>
            </div>
            <h1 class="font-display text-2xl font-bold text-secondary dark:text-white">Welcome back</h1>
            <p class="text-gray-500 dark:text-gray-400 text-sm mt-1">Sign in to your Gunaso account</p>
          </div>

          <!-- Error banner -->
          <div v-if="authStore.error" role="alert" class="mb-5 flex items-start gap-2.5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-3.5">
            <svg class="w-4 h-4 text-red-600 dark:text-red-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
            <p class="text-sm text-red-700 dark:text-red-400">{{ authStore.error }}</p>
          </div>

          <form @submit.prevent="handleSubmit" class="space-y-5" novalidate>
            <!-- Email -->
            <div>
              <label class="label" for="login-email">Email address</label>
              <input id="login-email" ref="emailInput" v-model="form.email" type="email" placeholder="you@example.com"
                :aria-invalid="!!fieldErrors.email"
                :class="['input-base', fieldErrors.email ? 'border-red-400 focus:border-red-400 focus:ring-red-200' : '']"
                autocomplete="email" />
              <p v-if="fieldErrors.email" class="field-error">{{ fieldErrors.email }}</p>
            </div>

            <!-- Password -->
            <div>
              <div class="flex items-center justify-between mb-1.5">
                <label class="label !mb-0" for="login-password">Password</label>
                <a href="#" class="text-xs text-primary hover:underline">Forgot password?</a>
              </div>
              <div class="relative">
                <input id="login-password" v-model="form.password" :type="showPassword ? 'text' : 'password'" placeholder="••••••••"
                  :aria-invalid="!!fieldErrors.password"
                  :class="['input-base pr-10', fieldErrors.password ? 'border-red-400 focus:border-red-400 focus:ring-red-200' : '']"
                  autocomplete="current-password" />
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
              <p v-if="fieldErrors.password" class="field-error">{{ fieldErrors.password }}</p>
            </div>

            <!-- Submit -->
            <button type="submit" :disabled="authStore.loading" class="btn-primary w-full py-3.5 text-base">
              <svg v-if="authStore.loading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              {{ authStore.loading ? 'Signing in...' : 'Sign In' }}
            </button>
          </form>

          <p class="text-center text-sm text-gray-500 dark:text-gray-400 mt-6">
            Don't have an account?
            <RouterLink to="/register" class="text-primary font-semibold hover:underline">Create one</RouterLink>
          </p>
        </div>

        <!-- Demo hint -->
        <div class="mt-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-3.5 text-center">
          <p class="text-xs text-blue-700 dark:text-blue-300">
            <span class="font-semibold">Demo:</span> citizen@gunaso.np / password123 &nbsp;|&nbsp; org@gunaso.np / password123
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
