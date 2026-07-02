<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const uiStore = useUIStore()

const form = ref({ email: '', password: '' })
const showPassword = ref(false)
const fieldErrors = ref({})

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
    uiStore.showSuccess(`Welcome back!`)
    const redirect = route.query.redirect
    router.push(redirect ? String(redirect) : authStore.isOrgAdmin ? '/org/dashboard' : '/dashboard')
  } catch {
    // error is set in the store
  }
}
</script>

<template>
  <div class="min-h-[calc(100vh-4rem)] bg-gradient-to-br from-secondary/5 via-app-bg to-primary/5 dark:from-gray-900 dark:via-gray-900 dark:to-gray-900 flex items-center justify-center p-4">
    <div class="w-full max-w-md">
      <!-- Card -->
      <div class="card p-8">
        <!-- Logo -->
        <div class="text-center mb-8">
          <div class="w-14 h-14 bg-primary rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-primary/20">
            <span class="text-white font-extrabold text-2xl">G</span>
          </div>
          <h1 class="text-2xl font-extrabold text-secondary dark:text-white">Welcome back</h1>
          <p class="text-gray-500 dark:text-gray-400 text-sm mt-1">Sign in to your Gunaso account</p>
        </div>

        <!-- Error banner -->
        <div v-if="authStore.error" class="mb-5 flex items-start gap-2.5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-3.5">
          <svg class="w-4 h-4 text-red-600 dark:text-red-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <p class="text-sm text-red-700 dark:text-red-400">{{ authStore.error }}</p>
        </div>

        <form @submit.prevent="handleSubmit" class="space-y-5">
          <!-- Email -->
          <div>
            <label class="label">Email address</label>
            <input v-model="form.email" type="email" placeholder="you@example.com"
              :class="['input-base', fieldErrors.email ? 'border-red-400 focus:border-red-400 focus:ring-red-200' : '']"
              autocomplete="email" />
            <p v-if="fieldErrors.email" class="field-error">{{ fieldErrors.email }}</p>
          </div>

          <!-- Password -->
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label class="label !mb-0">Password</label>
              <a href="#" class="text-xs text-primary hover:underline">Forgot password?</a>
            </div>
            <div class="relative">
              <input v-model="form.password" :type="showPassword ? 'text' : 'password'" placeholder="••••••••"
                :class="['input-base pr-10', fieldErrors.password ? 'border-red-400 focus:border-red-400 focus:ring-red-200' : '']"
                autocomplete="current-password" />
              <button type="button" @click="showPassword = !showPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                <svg v-if="!showPassword" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                </svg>
                <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
                </svg>
              </button>
            </div>
            <p v-if="fieldErrors.password" class="field-error">{{ fieldErrors.password }}</p>
          </div>

          <!-- Submit -->
          <button type="submit" :disabled="authStore.loading"
            class="btn-primary w-full py-3.5 text-base">
            <svg v-if="authStore.loading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
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
</template>
