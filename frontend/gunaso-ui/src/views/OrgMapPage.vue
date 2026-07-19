<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useAuthStore } from '@/stores/auth'
import { useOrganizationStore } from '@/stores/organization'
import { submissionsAPI } from '@/api/submissions'
import { apiErrorMessage } from '@/api/index'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const authStore = useAuthStore()
const orgStore = useOrganizationStore()

const canView = computed(() => authStore.hasPrivilege('view_submissions'))

const loading = ref(true)
const loadError = ref('')
const branches = ref([])
const recent = ref([])

const mapEl = ref(null)
let map = null
const markers = new Map() // branch id -> L.Marker
let bubbleTimer = null
let currentPopup = null

const prefersReducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false

const TYPE_META = {
  complaint: { icon: '⚠️', label: 'Complaint' },
  feedback: { icon: '💬', label: 'Feedback' },
  suggestion: { icon: '💡', label: 'Suggestion' },
}

function branchIcon(count) {
  return L.divIcon({
    className: '',
    html: `<div class="relative">
      <svg width="30" height="42" viewBox="0 0 30 42" xmlns="http://www.w3.org/2000/svg">
        <path d="M15 0C6.7 0 0 6.7 0 15c0 11.2 15 27 15 27s15-15.8 15-27C30 6.7 23.3 0 15 0z" fill="#1D3557"/>
        <circle cx="15" cy="15" r="6" fill="white"/>
      </svg>
      ${count > 0 ? `<span class="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-primary text-white text-[10px] font-bold flex items-center justify-center shadow">${count}</span>` : ''}
    </div>`,
    iconSize: [30, 42],
    iconAnchor: [15, 42],
    popupAnchor: [0, -38],
  })
}

function initMap() {
  map = L.map(mapEl.value)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(map)

  if (branches.value.length) {
    const bounds = L.latLngBounds(branches.value.map((b) => [b.latitude, b.longitude]))
    branches.value.forEach((b) => {
      const marker = L.marker([b.latitude, b.longitude], { icon: branchIcon(b.submission_count) })
        .addTo(map)
        .bindTooltip(b.name, { direction: 'top', offset: [0, -38] })
      markers.set(b.id, marker)
    })
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 })
  } else {
    map.setView([28.3949, 84.124], 6)
  }
}

function showBubble(entry) {
  const marker = markers.get(entry.branch_id)
  if (!marker || !map) return
  const meta = TYPE_META[entry.type] || { icon: '📋', label: entry.type }

  if (currentPopup) map.closePopup(currentPopup)

  const popup = L.popup({
    closeButton: false, autoClose: false, closeOnClick: false,
    className: 'thought-bubble-popup', offset: [0, -6],
  })
    .setLatLng(marker.getLatLng())
    .setContent(`
      <div class="animate-thought-bubble bg-white dark:bg-gray-800 rounded-2xl rounded-bl-sm shadow-lg border border-gray-100 px-3 py-2 max-w-[220px]">
        <p class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">${meta.icon} ${meta.label}</p>
        <p class="text-sm text-gray-800 dark:text-white leading-snug">${entry.excerpt}</p>
      </div>
    `)
    .openOn(map)

  currentPopup = popup
  setTimeout(() => {
    if (currentPopup === popup) {
      map?.closePopup(popup)
      currentPopup = null
    }
  }, 5800)
}

function startBubbleCycle() {
  if (prefersReducedMotion || !recent.value.length) return
  let i = 0
  const tick = () => {
    if (!recent.value.length) return
    showBubble(recent.value[i % recent.value.length])
    i += 1
    bubbleTimer = setTimeout(tick, 4500)
  }
  bubbleTimer = setTimeout(tick, 1200)
}

async function loadFeed() {
  loading.value = true
  loadError.value = ''
  try {
    const { data } = await submissionsAPI.mapFeed()
    branches.value = data.branches
    recent.value = data.recent
  } catch (err) {
    loadError.value = apiErrorMessage(err, 'Could not load the map feed.')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  if (!orgStore.currentOrg && authStore.accessibleOrgSlug) {
    await orgStore.fetchOrgBySlug(authStore.accessibleOrgSlug)
  }
  if (!canView.value) return
  await loadFeed()
  if (mapEl.value) {
    initMap()
    startBubbleCycle()
  }
})

onBeforeUnmount(() => {
  if (bubbleTimer) clearTimeout(bubbleTimer)
  if (map) {
    map.remove()
    map = null
  }
})
</script>

<template>
  <div class="p-6 space-y-5">
    <div>
      <h1 class="text-xl font-extrabold text-secondary dark:text-white">Branch Map</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
        Your branches, with recent gunaso popping up live so you can see where activity is coming from.
      </p>
    </div>

    <div v-if="!canView" class="card p-6 text-sm text-gray-600 dark:text-gray-300">
      You don't have permission to view submissions for this organization.
    </div>

    <template v-else>
      <LoadingSpinner v-if="loading" />

      <div v-else-if="loadError" class="card p-6 text-center text-sm text-red-500 dark:text-red-400">
        {{ loadError }}
      </div>

      <div v-else-if="!branches.length" class="card p-10 text-center">
        <p class="font-semibold text-gray-700 dark:text-gray-200">No branches on the map yet</p>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Add a branch with a location under
          <RouterLink to="/org/branches" class="text-primary hover:underline font-medium">Branches</RouterLink>
          to see it here.
        </p>
      </div>

      <div v-else class="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div ref="mapEl" class="lg:col-span-2 h-[520px] rounded-2xl overflow-hidden border border-gray-100 dark:border-gray-700 z-0"></div>

        <!-- Static recent list — always shown; doubles as the accessible /
             reduced-motion fallback for the animated map bubbles. -->
        <div class="card p-4 max-h-[520px] overflow-y-auto">
          <h2 class="text-sm font-bold text-gray-800 dark:text-white mb-3">Recent Gunaso</h2>
          <div v-if="!recent.length" class="text-sm text-gray-400 dark:text-gray-500 text-center py-6">
            No branch-linked gunaso yet.
          </div>
          <div v-else class="space-y-2.5">
            <div v-for="entry in recent" :key="entry.reference_number" class="p-2.5 rounded-xl bg-gray-50 dark:bg-gray-700/40">
              <p class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide">
                {{ TYPE_META[entry.type]?.icon || '📋' }}
                {{ branches.find((b) => b.id === entry.branch_id)?.name || 'Branch' }}
              </p>
              <p class="text-sm text-gray-800 dark:text-gray-200 mt-0.5">{{ entry.excerpt }}</p>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style>
/* Global (not scoped) — Leaflet renders these outside Vue's component tree. */
.thought-bubble-popup .leaflet-popup-content-wrapper {
  background: transparent;
  box-shadow: none;
  padding: 0;
}
.thought-bubble-popup .leaflet-popup-content {
  margin: 0;
}
.thought-bubble-popup .leaflet-popup-tip-container {
  display: none;
}
</style>
