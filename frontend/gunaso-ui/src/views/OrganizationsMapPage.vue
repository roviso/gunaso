<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { organizationsAPI } from '@/api/organizations'
import { apiErrorMessage } from '@/api/index'

const router = useRouter()

const mapEl = ref(null)
const loading = ref(true)
const error = ref(null)
const orgCount = ref(0)

let map = null

const NEPAL_CENTER = [28.3949, 84.124]

const pinIcon = L.divIcon({
  className: '',
  html: `<svg width="30" height="42" viewBox="0 0 30 42" xmlns="http://www.w3.org/2000/svg">
    <path d="M15 0C6.7 0 0 6.7 0 15c0 11.2 15 27 15 27s15-15.8 15-27C30 6.7 23.3 0 15 0z" fill="#E63946"/>
    <circle cx="15" cy="15" r="6" fill="white"/>
  </svg>`,
  iconSize: [30, 42],
  iconAnchor: [15, 42],
  tooltipAnchor: [0, -42],
})

// Org names/categories are user-supplied — always escape before embedding in
// tooltip HTML (same spirit as the no-unsanitized-v-html rule).
function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ))
}

function tooltipHtml(org) {
  const rating = org.average_rating != null
    ? `<span style="color:#f59e0b">&#9733;</span> <b>${Number(org.average_rating)}</b>
       <span style="color:#9ca3af">(${Number(org.rating_count)} rating${Number(org.rating_count) === 1 ? '' : 's'})</span>`
    : '<span style="color:#9ca3af">No public rating</span>'
  return `
    <div style="font-family:inherit; min-width:140px">
      <div style="font-weight:700">${esc(org.name)}</div>
      <div style="font-size:11px; color:#6b7280; margin-bottom:2px">${esc(org.category)}</div>
      <div style="font-size:12px">${rating}</div>
      <div style="font-size:11px; color:#9ca3af; margin-top:3px">Click to view profile</div>
    </div>`
}

async function loadMap() {
  loading.value = true
  error.value = null
  try {
    const { data } = await organizationsAPI.getLocations()
    orgCount.value = data.length

    map = L.map(mapEl.value).setView(NEPAL_CENTER, 7)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map)

    const bounds = []
    for (const org of data) {
      const marker = L.marker([org.latitude, org.longitude], { icon: pinIcon }).addTo(map)
      marker.bindTooltip(tooltipHtml(org), { direction: 'top', opacity: 1 })
      marker.on('click', () => router.push(`/organizations/${org.slug}`))
      bounds.push([org.latitude, org.longitude])
    }
    if (bounds.length) map.fitBounds(bounds, { padding: [60, 60], maxZoom: 14 })
  } catch (err) {
    error.value = apiErrorMessage(err, 'Could not load the organizations map.')
  } finally {
    loading.value = false
  }
}

onMounted(loadMap)

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
  }
})
</script>

<template>
  <div class="relative h-[calc(100vh-4rem)] bg-app-bg dark:bg-gray-900">
    <div ref="mapEl" class="absolute inset-0 z-0"></div>

    <!-- Overlay: title + status -->
    <div class="absolute top-4 left-4 z-[1000] card px-4 py-3 shadow-lg max-w-xs">
      <h1 class="font-display font-bold text-secondary dark:text-white text-base leading-tight">Organizations Map</h1>
      <p v-if="loading" class="text-xs text-gray-500 dark:text-gray-400 mt-1">Loading organizations…</p>
      <p v-else-if="error" class="text-xs text-red-500 mt-1">{{ error }}</p>
      <p v-else-if="orgCount === 0" class="text-xs text-gray-500 dark:text-gray-400 mt-1">
        No organizations have shared their location yet.
      </p>
      <p v-else class="text-xs text-gray-500 dark:text-gray-400 mt-1">
        {{ orgCount }} organization{{ orgCount === 1 ? '' : 's' }} — hover a pin for its rating, click to view the profile.
      </p>
    </div>
  </div>
</template>
