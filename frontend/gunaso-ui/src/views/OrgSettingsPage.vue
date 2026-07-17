<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useOrganizationStore } from '@/stores/organization'
import { useUIStore } from '@/stores/ui'
import { apiErrorMessage } from '@/api/index'

const authStore = useAuthStore()
const orgStore = useOrganizationStore()
const uiStore = useUIStore()

const categories = ['Government', 'Telecom', 'Bank', 'Hospital', 'Education', 'Transport', 'Utility', 'Insurance', 'Retail', 'Other']

const canEdit = computed(() => authStore.hasPrivilege('manage_org_profile'))

const form = ref({
  name: '', category: '', website: '', description: '',
  contact_email: '', contact_phone: '', address: ''
})
const fieldErrors = ref({})
const saving = ref(false)

const logoFile = ref(null)
const logoObjectUrl = ref(null)
const fileInputRef = ref(null)

const logoPreview = computed(() => logoObjectUrl.value || orgStore.currentOrg?.logo || null)

function populateForm(org) {
  if (!org) return
  form.value = {
    name: org.name || '',
    category: org.category || '',
    website: org.website || '',
    description: org.description || '',
    contact_email: org.contact_email || '',
    contact_phone: org.contact_phone || '',
    address: org.address || ''
  }
}

onMounted(async () => {
  if (!orgStore.currentOrg && authStore.accessibleOrgSlug) {
    await orgStore.fetchOrgBySlug(authStore.accessibleOrgSlug)
  }
  populateForm(orgStore.currentOrg)
})

onBeforeUnmount(() => {
  if (logoObjectUrl.value) URL.revokeObjectURL(logoObjectUrl.value)
})

function handleLogoChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  logoFile.value = file
  if (logoObjectUrl.value) URL.revokeObjectURL(logoObjectUrl.value)
  logoObjectUrl.value = URL.createObjectURL(file)
}

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
  if (!validate() || saving.value) return
  saving.value = true
  try {
    const slug = orgStore.currentOrg.slug
    let payload
    if (logoFile.value) {
      payload = new FormData()
      Object.entries(form.value).forEach(([key, value]) => payload.append(key, value))
      payload.append('logo', logoFile.value)
    } else {
      payload = { ...form.value }
    }
    await orgStore.updateSettings(slug, payload)
    logoFile.value = null
    uiStore.showSuccess('Organization profile updated.')
  } catch (err) {
    uiStore.showError(apiErrorMessage(err, 'Could not update organization profile.'))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="page-container py-8 max-w-3xl">
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Organization Settings</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Manage your organization's public profile information.</p>
    </div>

    <div v-if="!canEdit" class="card p-6 text-sm text-gray-600 dark:text-gray-300">
      You don't have permission to edit this organization's profile.
    </div>

    <div v-else class="card p-8">
      <form @submit.prevent="handleSubmit" class="space-y-5">
        <!-- Logo -->
        <div class="flex items-center gap-4">
          <div class="w-16 h-16 rounded-2xl bg-gray-100 dark:bg-gray-700 overflow-hidden flex items-center justify-center shrink-0">
            <img v-if="logoPreview" :src="logoPreview" alt="Organization logo" class="w-full h-full object-cover" />
            <span v-else class="text-xl font-bold text-gray-400">{{ form.name?.[0]?.toUpperCase() || 'O' }}</span>
          </div>
          <div>
            <button type="button" @click="fileInputRef?.click()" class="btn-secondary !px-4 !py-2 text-sm">
              Change logo
            </button>
            <input ref="fileInputRef" type="file" accept="image/*" class="hidden" @change="handleLogoChange" />
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <div class="sm:col-span-2">
            <label class="label">Organization Name *</label>
            <input v-model="form.name" type="text"
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
            <textarea v-model="form.description" rows="4"
              :class="['input-base resize-none', fieldErrors.description ? 'border-red-400' : '']" />
            <p v-if="fieldErrors.description" class="field-error">{{ fieldErrors.description }}</p>
          </div>

          <div>
            <label class="label">Contact Email *</label>
            <input v-model="form.contact_email" type="email"
              :class="['input-base', fieldErrors.contact_email ? 'border-red-400' : '']" />
            <p v-if="fieldErrors.contact_email" class="field-error">{{ fieldErrors.contact_email }}</p>
          </div>

          <div>
            <label class="label">Contact Phone (optional)</label>
            <input v-model="form.contact_phone" type="tel" class="input-base" />
          </div>

          <div class="sm:col-span-2">
            <label class="label">Address (optional)</label>
            <input v-model="form.address" type="text" class="input-base" />
          </div>
        </div>

        <div class="flex justify-end">
          <button type="submit" :disabled="saving" class="btn-primary">
            <svg v-if="saving" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            {{ saving ? 'Saving...' : 'Save Changes' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
