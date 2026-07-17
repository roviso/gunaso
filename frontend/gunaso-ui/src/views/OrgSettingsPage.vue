<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
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
  contact_email: '', contact_phone: '', address: '',
  show_rating: true, latitude: null, longitude: null
})
const fieldErrors = ref({})
const saving = ref(false)

const logoFile = ref(null)
const logoObjectUrl = ref(null)
const fileInputRef = ref(null)

const logoPreview = computed(() => logoObjectUrl.value || orgStore.currentOrg?.logo || null)

// ── Location picker ──────────────────────────────────────────────────────
const NEPAL_CENTER = [28.3949, 84.124]
const mapEl = ref(null)
let map = null
let marker = null

const pinIcon = L.divIcon({
  className: '',
  html: `<svg width="30" height="42" viewBox="0 0 30 42" xmlns="http://www.w3.org/2000/svg">
    <path d="M15 0C6.7 0 0 6.7 0 15c0 11.2 15 27 15 27s15-15.8 15-27C30 6.7 23.3 0 15 0z" fill="#E63946"/>
    <circle cx="15" cy="15" r="6" fill="white"/>
  </svg>`,
  iconSize: [30, 42],
  iconAnchor: [15, 42],
})

function placeMarker(lat, lng) {
  if (!map) return
  if (marker) {
    marker.setLatLng([lat, lng])
  } else {
    marker = L.marker([lat, lng], { icon: pinIcon }).addTo(map)
  }
}

function setLocation(lat, lng) {
  form.value.latitude = Number(lat.toFixed(6))
  form.value.longitude = Number(lng.toFixed(6))
  placeMarker(lat, lng)
}

function clearLocation() {
  form.value.latitude = null
  form.value.longitude = null
  if (marker) {
    marker.remove()
    marker = null
  }
}

function syncMarkerFromInputs() {
  const lat = Number(form.value.latitude)
  const lng = Number(form.value.longitude)
  if (Number.isFinite(lat) && Number.isFinite(lng) && lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) {
    placeMarker(lat, lng)
    map?.setView([lat, lng], Math.max(map.getZoom(), 12))
  }
}

function initMap() {
  if (!mapEl.value || map) return
  const hasLocation = form.value.latitude != null && form.value.longitude != null
  const center = hasLocation ? [Number(form.value.latitude), Number(form.value.longitude)] : NEPAL_CENTER
  map = L.map(mapEl.value).setView(center, hasLocation ? 13 : 6)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(map)
  if (hasLocation) placeMarker(center[0], center[1])
  map.on('click', (e) => setLocation(e.latlng.lat, e.latlng.lng))
}

function populateForm(org) {
  if (!org) return
  form.value = {
    name: org.name || '',
    category: org.category || '',
    website: org.website || '',
    description: org.description || '',
    contact_email: org.contact_email || '',
    contact_phone: org.contact_phone || '',
    address: org.address || '',
    show_rating: org.show_rating !== false,
    latitude: org.latitude != null ? Number(org.latitude) : null,
    longitude: org.longitude != null ? Number(org.longitude) : null
  }
}

onMounted(async () => {
  if (!orgStore.currentOrg && authStore.accessibleOrgSlug) {
    await orgStore.fetchOrgBySlug(authStore.accessibleOrgSlug)
  }
  populateForm(orgStore.currentOrg)
  await nextTick()
  if (canEdit.value) initMap()
})

onBeforeUnmount(() => {
  if (logoObjectUrl.value) URL.revokeObjectURL(logoObjectUrl.value)
  if (map) {
    map.remove()
    map = null
    marker = null
  }
})

function handleLogoChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  logoFile.value = file
  if (logoObjectUrl.value) URL.revokeObjectURL(logoObjectUrl.value)
  logoObjectUrl.value = URL.createObjectURL(file)
}

// Empty <input type="number"> yields '' — treat that as unset.
function coordOrNull(value) {
  return value === '' || value == null ? null : Number(value)
}

function validate() {
  fieldErrors.value = {}
  if (!form.value.name.trim()) fieldErrors.value.name = 'Organization name is required.'
  if (!form.value.category) fieldErrors.value.category = 'Please select a category.'
  if (!form.value.description.trim()) fieldErrors.value.description = 'Description is required.'
  else if (form.value.description.trim().length < 30) fieldErrors.value.description = 'Please provide at least 30 characters.'
  if (!form.value.contact_email.trim()) fieldErrors.value.contact_email = 'Contact email is required.'
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.value.contact_email)) fieldErrors.value.contact_email = 'Enter a valid email.'
  const lat = coordOrNull(form.value.latitude)
  const lng = coordOrNull(form.value.longitude)
  if ((lat == null) !== (lng == null)) fieldErrors.value.location = 'Set both latitude and longitude, or clear both.'
  else if (lat != null && (lat < -90 || lat > 90)) fieldErrors.value.location = 'Latitude must be between -90 and 90.'
  else if (lng != null && (lng < -180 || lng > 180)) fieldErrors.value.location = 'Longitude must be between -180 and 180.'
  return Object.keys(fieldErrors.value).length === 0
}

async function handleSubmit() {
  if (!validate() || saving.value) return
  saving.value = true
  try {
    const slug = orgStore.currentOrg.slug
    // Data fields always go as JSON so latitude/longitude can be cleared with
    // an explicit null (multipart can't encode null); the logo, when changed,
    // goes in its own multipart PATCH right after.
    await orgStore.updateSettings(slug, {
      ...form.value,
      latitude: coordOrNull(form.value.latitude),
      longitude: coordOrNull(form.value.longitude),
    })
    if (logoFile.value) {
      const logoPayload = new FormData()
      logoPayload.append('logo', logoFile.value)
      await orgStore.updateSettings(slug, logoPayload)
      logoFile.value = null
    }
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

        <!-- Rating visibility -->
        <div class="flex items-start justify-between gap-4 pt-5 border-t border-gray-100 dark:border-gray-700">
          <div>
            <p class="text-sm font-semibold text-gray-900 dark:text-white">Show average rating publicly</p>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5 max-w-md">
              Citizens can always rate your organization. This controls whether the average
              is displayed on your public profile, in search results, and on the map.
            </p>
          </div>
          <button type="button" role="switch" :aria-checked="form.show_rating"
            @click="form.show_rating = !form.show_rating"
            :class="['relative inline-flex h-6 w-11 rounded-full transition-colors duration-200 shrink-0 mt-0.5',
              form.show_rating ? 'bg-primary' : 'bg-gray-300 dark:bg-gray-600']">
            <span :class="['inline-block h-5 w-5 mt-0.5 rounded-full bg-white shadow transform transition-transform duration-200',
              form.show_rating ? 'translate-x-[22px]' : 'translate-x-0.5']" />
          </button>
        </div>

        <!-- Location -->
        <div class="pt-5 border-t border-gray-100 dark:border-gray-700">
          <p class="text-sm font-semibold text-gray-900 dark:text-white">Location (optional)</p>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5 mb-3">
            Click the map to place your organization — it will then appear on the public organizations map.
          </p>
          <div ref="mapEl" class="h-64 rounded-xl overflow-hidden border border-gray-200 dark:border-gray-600 z-0"></div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3 items-end">
            <div>
              <label class="label">Latitude</label>
              <input v-model.number="form.latitude" type="number" step="any" min="-90" max="90"
                @change="syncMarkerFromInputs" class="input-base" placeholder="27.7172" />
            </div>
            <div>
              <label class="label">Longitude</label>
              <input v-model.number="form.longitude" type="number" step="any" min="-180" max="180"
                @change="syncMarkerFromInputs" class="input-base" placeholder="85.3240" />
            </div>
            <button type="button" @click="clearLocation"
              :disabled="form.latitude == null && form.longitude == null"
              class="btn-secondary !py-3 text-sm disabled:opacity-50 disabled:cursor-not-allowed">
              Clear location
            </button>
          </div>
          <p v-if="fieldErrors.location" class="field-error">{{ fieldErrors.location }}</p>
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
