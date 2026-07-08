<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { organizationsAPI } from '@/api/organizations'
import { apiErrorMessage } from '@/api/index'
import { useUIStore } from '@/stores/ui'

const router = useRouter()
const uiStore = useUIStore()

const loading = ref(false)
const submitted = ref(false)
const fieldErrors = ref({})

const form = ref({
  name: '', category: '', website: '', description: '',
  contact_email: '', contact_phone: '', address: ''
})

const categories = ['Government', 'Telecom', 'Bank', 'Hospital', 'Education', 'Transport', 'Utility', 'Insurance', 'Retail', 'Other']

function validate() {
  fieldErrors.value = {}
  if (!form.value.name.trim()) fieldErrors.value.name = 'Organization name is required.'
  if (!form.value.category) fieldErrors.value.category = 'Please select a category.'
  if (!form.value.description.trim()) fieldErrors.value.description = 'Description is required.'
  else if (form.value.description.trim().length < 30) fieldErrors.value.description = 'Please provide at least 30 characters.'
  if (!form.value.contact_email.trim()) fieldErrors.value.contact_email = 'Contact email is required.'
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.value.contact_email)) fieldErrors.value.contact_email = 'Enter a valid email.'
  return Object.keys(fieldErrors.value).length === 0
}

async function handleSubmit() {
  if (!validate()) return
  loading.value = true
  try {
    await organizationsAPI.register(form.value)
    submitted.value = true
    uiStore.showSuccess('Organization registration submitted!')
  } catch (err) {
    uiStore.showError(apiErrorMessage(err, 'Registration failed. Please try again.'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="bg-app-bg dark:bg-gray-900 min-h-[calc(100vh-4rem)]">
    <!-- Header -->
    <div class="bg-gradient-to-br from-secondary to-[#0f1f38] text-white py-12">
      <div class="page-container">
        <div class="max-w-2xl">
          <h1 class="text-3xl font-extrabold mb-2">Register Your Organization</h1>
          <p class="text-blue-200">Join Gunaso as a verified organization. Receive and respond to citizen feedback directly.</p>
        </div>
      </div>
    </div>

    <div class="page-container py-10">
      <!-- Success state -->
      <div v-if="submitted" class="max-w-lg mx-auto text-center py-12">
        <div class="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-5">
          <svg class="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
          </svg>
        </div>
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-3">Application Submitted!</h2>
        <p class="text-gray-500 dark:text-gray-400 mb-6">Your organization registration is under review. We'll verify the information and contact you at <span class="font-medium text-gray-700 dark:text-gray-300">{{ form.contact_email }}</span> within 2-3 business days.</p>
        <RouterLink to="/" class="btn-primary">Back to Home</RouterLink>
      </div>

      <!-- Form -->
      <div v-else class="max-w-2xl mx-auto">
        <div class="card p-8">
          <h2 class="text-xl font-bold text-gray-900 dark:text-white mb-6">Organization Details</h2>
          <form @submit.prevent="handleSubmit" class="space-y-5">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div class="sm:col-span-2">
                <label class="label">Organization Name *</label>
                <input v-model="form.name" type="text" placeholder="e.g. Nepal Telecom"
                  :class="['input-base', fieldErrors.name ? 'border-red-400' : '']" />
                <p v-if="fieldErrors.name" class="field-error">{{ fieldErrors.name }}</p>
              </div>

              <div>
                <label class="label">Category *</label>
                <select v-model="form.category" :class="['input-base', fieldErrors.category ? 'border-red-400' : '']">
                  <option value="">Select category</option>
                  <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
                </select>
                <p v-if="fieldErrors.category" class="field-error">{{ fieldErrors.category }}</p>
              </div>

              <div>
                <label class="label">Website (optional)</label>
                <input v-model="form.website" type="url" placeholder="https://example.com" class="input-base" />
              </div>

              <div class="sm:col-span-2">
                <label class="label">Description *</label>
                <textarea v-model="form.description" rows="4" placeholder="Brief description of your organization and the services you provide..."
                  :class="['input-base resize-none', fieldErrors.description ? 'border-red-400' : '']" />
                <p v-if="fieldErrors.description" class="field-error">{{ fieldErrors.description }}</p>
              </div>

              <div>
                <label class="label">Contact Email *</label>
                <input v-model="form.contact_email" type="email" placeholder="complaints@organization.np"
                  :class="['input-base', fieldErrors.contact_email ? 'border-red-400' : '']" />
                <p v-if="fieldErrors.contact_email" class="field-error">{{ fieldErrors.contact_email }}</p>
              </div>

              <div>
                <label class="label">Contact Phone (optional)</label>
                <input v-model="form.contact_phone" type="tel" placeholder="+977-01-XXXXXXX" class="input-base" />
              </div>

              <div class="sm:col-span-2">
                <label class="label">Address (optional)</label>
                <input v-model="form.address" type="text" placeholder="Kathmandu, Nepal" class="input-base" />
              </div>
            </div>

            <div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-4 text-sm text-blue-800 dark:text-blue-300">
              <p class="font-semibold mb-1">Verification Process</p>
              <p>Your registration will be reviewed by our team within 2–3 business days. You'll receive an email with your login credentials once approved.</p>
            </div>

            <button type="submit" :disabled="loading" class="btn-primary w-full py-3.5 text-base">
              <svg v-if="loading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              {{ loading ? 'Submitting...' : 'Submit Registration' }}
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>
