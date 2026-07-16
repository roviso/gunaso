<script setup>
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { apiErrorMessage } from '@/api/index'

const authStore = useAuthStore()

const editing = ref(false)
const emailDraft = ref('')
const sending = ref(false)
const sent = ref(false)
const error = ref('')

function startEdit() {
  emailDraft.value = authStore.user?.email || ''
  editing.value = true
}

async function send(payload = {}) {
  sending.value = true
  error.value = ''
  try {
    await authStore.requestEmailVerification(payload)
    sent.value = true
    editing.value = false
  } catch (err) {
    error.value = apiErrorMessage(err, 'Could not send the verification email.')
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <div v-if="authStore.isAuthenticated && authStore.user?.email_verified === false && !sent"
    class="bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800 px-4 py-2.5">
    <div class="flex items-center flex-wrap gap-2 text-sm">
      <svg class="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
      </svg>

      <template v-if="!editing">
        <span class="text-amber-800 dark:text-amber-300">
          Your email <span class="font-semibold">{{ authStore.user?.email }}</span> hasn't been verified yet.
        </span>
        <button @click="send()" :disabled="sending" class="font-semibold text-amber-900 dark:text-amber-200 underline underline-offset-2 hover:no-underline disabled:opacity-50">
          {{ sending ? 'Sending…' : 'Send verification link' }}
        </button>
        <button @click="startEdit" class="text-amber-700 dark:text-amber-400 underline underline-offset-2 hover:no-underline">
          Wrong email? Fix it
        </button>
      </template>

      <template v-else>
        <input v-model="emailDraft" type="email" placeholder="you@example.com"
          class="px-2 py-1 rounded-lg border border-amber-300 dark:border-amber-700 bg-white dark:bg-gray-800 text-sm text-gray-800 dark:text-gray-100 w-64 max-w-full" />
        <button @click="send({ email: emailDraft })" :disabled="sending || !emailDraft" class="font-semibold text-amber-900 dark:text-amber-200 underline underline-offset-2 hover:no-underline disabled:opacity-50">
          {{ sending ? 'Sending…' : 'Save & send' }}
        </button>
        <button @click="editing = false" class="text-amber-700 dark:text-amber-400 underline underline-offset-2 hover:no-underline">Cancel</button>
      </template>

      <span v-if="error" class="text-red-600 dark:text-red-400">{{ error }}</span>
    </div>
  </div>

  <div v-else-if="authStore.isAuthenticated && sent"
    class="bg-green-50 dark:bg-green-900/20 border-b border-green-200 dark:border-green-800 px-4 py-2.5 text-sm text-green-800 dark:text-green-300">
    Verification email sent — check your inbox and click the link to finish securing your account.
  </div>
</template>
