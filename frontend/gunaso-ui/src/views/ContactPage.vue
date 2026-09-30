<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { publicAPI } from '@/api/public'
import { apiErrorMessage } from '@/api/index'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const authStore = useAuthStore()

const TOPICS = [
  { value: 'general', label: 'General question' },
  { value: 'organization', label: 'Bring my organization to Gunaso' },
  { value: 'support', label: 'Help with a gunaso I filed' },
  { value: 'press', label: 'Press & partnerships' },
  { value: 'other', label: 'Something else' },
]

const form = ref({
  name: authStore.user?.name || '',
  email: authStore.user?.email || '',
  organization: '',
  topic: TOPICS.some((t) => t.value === route.query.topic) ? route.query.topic : 'general',
  message: '',
  website: '', // honeypot — hidden from humans
})
const errors = ref({})
const sending = ref(false)
const sent = ref(false)
const serverError = ref('')

function validate() {
  const e = {}
  if (!form.value.name.trim()) e.name = 'Please tell us your name.'
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.value.email)) e.email = 'Enter a valid email so we can reply.'
  if (form.value.message.trim().length < 10) e.message = 'A little more detail, please (10+ characters).'
  errors.value = e
  return !Object.keys(e).length
}

async function submit() {
  if (!validate() || sending.value) return
  sending.value = true
  serverError.value = ''
  try {
    await publicAPI.contact({ ...form.value, name: form.value.name.trim(), message: form.value.message.trim() })
    sent.value = true
  } catch (err) {
    const fieldErrors = err?.response?.data?.error?.field_errors || {}
    errors.value = Object.fromEntries(
      Object.entries(fieldErrors).map(([k, v]) => [k, Array.isArray(v) ? v[0] : String(v)])
    )
    if (err?.response?.status === 429) {
      serverError.value = 'You’ve sent several messages recently — please try again in a little while.'
    } else if (!Object.keys(fieldErrors).length) {
      serverError.value = apiErrorMessage(err, 'Could not send your message. Please try again.')
    }
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <div class="bg-app-bg dark:bg-gray-900 min-h-[calc(100vh-4rem)]">
    <div class="page-container py-14 sm:py-20 grid lg:grid-cols-[1fr,1.3fr] gap-12 max-w-6xl">
      <div>
        <p class="text-xs font-bold uppercase tracking-[0.2em] text-primary mb-3">Contact</p>
        <h1 class="font-display text-4xl font-extrabold text-secondary dark:text-white tracking-tight mb-4">Talk to the Gunaso team</h1>
        <p class="text-gray-600 dark:text-gray-300 leading-relaxed mb-8">
          Onboarding an organization, a partnership idea, or a question we haven’t answered — send us a note and a person will reply.
        </p>
        <div class="space-y-4">
          <div class="card p-5">
            <p class="font-semibold text-gray-900 dark:text-white">Have a problem with an organization?</p>
            <p class="text-sm text-gray-600 dark:text-gray-300 mt-1">That’s what a gunaso is for — it goes straight to them, on the record.</p>
            <RouterLink to="/submit" class="text-sm font-semibold text-primary hover:underline mt-2 inline-block">File a gunaso →</RouterLink>
          </div>
          <div class="card p-5">
            <p class="font-semibold text-gray-900 dark:text-white">Checking on one you filed?</p>
            <p class="text-sm text-gray-600 dark:text-gray-300 mt-1">Use your GUN- reference to see its status and history.</p>
            <RouterLink :to="{ name: 'Track' }" class="text-sm font-semibold text-primary hover:underline mt-2 inline-block">Track a gunaso →</RouterLink>
          </div>
        </div>
      </div>

      <div class="card !rounded-3xl p-6 sm:p-8">
        <div v-if="sent" class="text-center py-10">
          <div class="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-5">
            <svg class="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>
          </div>
          <h2 class="text-xl font-bold text-gray-900 dark:text-white">Message received</h2>
          <p class="text-gray-500 dark:text-gray-400 mt-2">We’ll reply to {{ form.email }} as soon as we can.</p>
          <RouterLink to="/" class="btn-secondary mt-6">Back to home</RouterLink>
        </div>

        <form v-else class="space-y-5" novalidate @submit.prevent="submit">
          <div class="grid sm:grid-cols-2 gap-4">
            <div>
              <label for="c-name" class="label">Your name</label>
              <input id="c-name" v-model="form.name" type="text" autocomplete="name" maxlength="200"
                :class="['input-base', errors.name ? 'border-red-400' : '']" />
              <p v-if="errors.name" class="field-error">{{ errors.name }}</p>
            </div>
            <div>
              <label for="c-email" class="label">Email</label>
              <input id="c-email" v-model="form.email" type="email" autocomplete="email"
                :class="['input-base', errors.email ? 'border-red-400' : '']" />
              <p v-if="errors.email" class="field-error">{{ errors.email }}</p>
            </div>
          </div>
          <div>
            <label for="c-topic" class="label">What’s it about?</label>
            <select id="c-topic" v-model="form.topic" class="input-base">
              <option v-for="t in TOPICS" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>
          <div v-if="form.topic === 'organization' || form.topic === 'press'">
            <label for="c-org" class="label">Organization <span class="font-normal text-gray-400">(optional)</span></label>
            <input id="c-org" v-model="form.organization" type="text" autocomplete="organization" maxlength="255" class="input-base" />
          </div>
          <div>
            <label for="c-msg" class="label">Message</label>
            <textarea id="c-msg" v-model="form.message" rows="6" maxlength="5000"
              :class="['input-base resize-none', errors.message ? 'border-red-400' : '']" />
            <p v-if="errors.message" class="field-error">{{ errors.message }}</p>
          </div>
          <!-- Honeypot: visually hidden and skipped by keyboard/screen readers. -->
          <div class="absolute -left-[9999px] w-px h-px overflow-hidden" aria-hidden="true">
            <label for="c-website">Website</label>
            <input id="c-website" v-model="form.website" type="text" tabindex="-1" autocomplete="off" />
          </div>
          <p v-if="serverError" class="text-sm text-red-600 dark:text-red-400">{{ serverError }}</p>
          <button type="submit" :disabled="sending" class="btn-primary w-full !py-3.5">
            {{ sending ? 'Sending…' : 'Send message' }}
          </button>
          <p class="text-xs text-gray-400 dark:text-gray-500 text-center">
            We only use your details to reply. See our <RouterLink to="/privacy" class="underline">privacy policy</RouterLink>.
          </p>
        </form>
      </div>
    </div>
  </div>
</template>
