<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'

const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUIStore()

const form = ref({
  name: '', email: '', password: '', confirmPassword: '',
  user_type: 'citizen'
})
const fieldErrors = ref({})
const showPassword = ref(false)

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
    router.push(authStore.isOrgAdmin ? '/org/dashboard' : '/dashboard')
  } catch (err) {
    // errors shown from store
  }
}
</script>

<template>
  <div class="min-h-[calc(100vh-4rem)] bg-gradient-to-br from-secondary/5 via-app-bg to-primary/5 dark:from-gray-900 dark:via-gray-900 dark:to-gray-900 flex items-center justify-center p-4 py-10">
    <div class="w-full max-w-md">
      <div class="card p-8">
        <div class="text-center mb-8">
          <div class="w-14 h-14 bg-primary rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-primary/20">
            <span class="text-white font-extrabold text-2xl">G</span>
          </div>
          <h1 class="text-2xl font-extrabold text-secondary dark:text-white">Create your account</h1>
          <p class="text-gray-500 dark:text-gray-400 text-sm mt-1">Join thousands of citizens on Gunaso</p>
        </div>

        <!-- Account Type -->
        <div class="grid grid-cols-2 gap-3 mb-6">
          <button v-for="type in [{ value: 'citizen', label: 'Citizen', icon: '👤', desc: 'Submit & track complaints' }, { value: 'org_admin', label: 'Organization', icon: '🏢', desc: 'Manage your inbox' }]"
            :key="type.value"
            @click="form.user_type = type.value"
            :class="['p-3.5 rounded-xl border-2 text-left transition-all duration-150',
              form.user_type === type.value
                ? 'border-primary bg-primary/5 dark:bg-primary/10'
                : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500']">
            <span class="text-2xl block mb-1">{{ type.icon }}</span>
            <p :class="['text-sm font-semibold', form.user_type === type.value ? 'text-primary' : 'text-gray-900 dark:text-white']">{{ type.label }}</p>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{{ type.desc }}</p>
          </button>
        </div>

        <!-- Server errors -->
        <div v-if="authStore.error && typeof authStore.error === 'object'" class="mb-5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-3.5">
          <p v-for="(msgs, field) in authStore.error" :key="field" class="text-sm text-red-700 dark:text-red-400">
            <span class="font-medium capitalize">{{ field }}:</span> {{ Array.isArray(msgs) ? msgs[0] : msgs }}
          </p>
        </div>

        <form @submit.prevent="handleSubmit" class="space-y-4">
          <div>
            <label class="label">Full name</label>
            <input v-model="form.name" type="text" placeholder="Ram Prasad Sharma"
              :class="['input-base', fieldErrors.name ? 'border-red-400' : '']" autocomplete="name" />
            <p v-if="fieldErrors.name" class="field-error">{{ fieldErrors.name }}</p>
          </div>

          <div>
            <label class="label">Email address</label>
            <input v-model="form.email" type="email" placeholder="you@example.com"
              :class="['input-base', fieldErrors.email ? 'border-red-400' : '']" autocomplete="email" />
            <p v-if="fieldErrors.email" class="field-error">{{ fieldErrors.email }}</p>
          </div>

          <div>
            <label class="label">Password</label>
            <div class="relative">
              <input v-model="form.password" :type="showPassword ? 'text' : 'password'" placeholder="Minimum 8 characters"
                :class="['input-base pr-10', fieldErrors.password ? 'border-red-400' : '']" autocomplete="new-password" />
              <button type="button" @click="showPassword = !showPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                </svg>
              </button>
            </div>
            <p v-if="fieldErrors.password" class="field-error">{{ fieldErrors.password }}</p>
          </div>

          <div>
            <label class="label">Confirm password</label>
            <input v-model="form.confirmPassword" :type="showPassword ? 'text' : 'password'" placeholder="Repeat password"
              :class="['input-base', fieldErrors.confirmPassword ? 'border-red-400' : '']" autocomplete="new-password" />
            <p v-if="fieldErrors.confirmPassword" class="field-error">{{ fieldErrors.confirmPassword }}</p>
          </div>

          <button type="submit" :disabled="authStore.loading" class="btn-primary w-full py-3.5 text-base mt-2">
            <svg v-if="authStore.loading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
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
</template>
