<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { apiErrorMessage } from '@/api/index'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const authStore = useAuthStore()

const token = String(route.params.token || '')
const status = ref('loading') // 'loading' | 'success' | 'error'
const errorMessage = ref('')

onMounted(async () => {
  if (!token) {
    status.value = 'error'
    errorMessage.value = 'This verification link is missing its token.'
    return
  }
  try {
    await authStore.confirmEmailVerification(token)
    status.value = 'success'
  } catch (err) {
    status.value = 'error'
    errorMessage.value = apiErrorMessage(err, 'This verification link is invalid or has expired.')
  }
})
</script>

<template>
  <div class="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4 bg-app-bg dark:bg-gray-900">
    <div class="w-full max-w-md animate-fade-up">
      <div class="card p-8 text-center">
        <div v-if="status === 'loading'">
          <LoadingSpinner label="Verifying your email..." />
        </div>

        <div v-else-if="status === 'success'">
          <div class="w-14 h-14 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-5">
            <svg class="w-7 h-7 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
          </div>
          <h1 class="font-display text-xl font-bold text-secondary dark:text-white mb-2">Email verified</h1>
          <p class="text-gray-500 dark:text-gray-400 text-sm leading-relaxed mb-6">
            Your account is fully set up.
          </p>
          <RouterLink :to="authStore.isAuthenticated ? (authStore.hasOrgAccess ? '/org/dashboard' : '/dashboard') : '/login'" class="btn-primary">
            {{ authStore.isAuthenticated ? 'Continue' : 'Sign In' }}
          </RouterLink>
        </div>

        <div v-else>
          <div class="w-14 h-14 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-5">
            <svg class="w-7 h-7 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
          <h1 class="font-display text-xl font-bold text-secondary dark:text-white mb-2">Couldn't verify this link</h1>
          <p class="text-gray-500 dark:text-gray-400 text-sm leading-relaxed mb-6">{{ errorMessage }}</p>
          <RouterLink to="/" class="btn-secondary">Back to Home</RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>
