<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { NEPAL_CENTER, addBaseTiles, pinIcon as makePin } from '@/utils/map'

// v-model: { latitude: number|null, longitude: number|null }. Click the map
// (or edit the number inputs) to place/move a single marker; "Clear" resets
// both to null. Reused by OrgSettingsPage (organization location) and
// OrgBranchesPage (per-branch location).
const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({ latitude: null, longitude: null })
  },
  height: { type: String, default: 'h-64' }
})
const emit = defineEmits(['update:modelValue'])

const mapEl = ref(null)
const locating = ref(false)
const locateError = ref('')
let map = null
let marker = null

const pinIcon = makePin({ color: '#E63946' })

function useMyLocation() {
  if (!navigator.geolocation) {
    locateError.value = 'Your browser does not support location.'
    return
  }
  locating.value = true
  locateError.value = ''
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      locating.value = false
      setLocation(pos.coords.latitude, pos.coords.longitude)
      map?.setView([pos.coords.latitude, pos.coords.longitude], 16)
    },
    () => {
      locating.value = false
      locateError.value = 'Location permission was denied — click the map instead.'
    },
    { enableHighAccuracy: true, timeout: 10000 },
  )
}

function placeMarker(lat, lng) {
  if (!map) return
  if (marker) {
    marker.setLatLng([lat, lng])
  } else {
    marker = L.marker([lat, lng], { icon: pinIcon }).addTo(map)
  }
}

function setLocation(lat, lng) {
  emit('update:modelValue', {
    latitude: Number(lat.toFixed(6)),
    longitude: Number(lng.toFixed(6)),
  })
}

function clearLocation() {
  emit('update:modelValue', { latitude: null, longitude: null })
  if (marker) {
    marker.remove()
    marker = null
  }
}

function syncMarkerFromValue() {
  const lat = Number(props.modelValue?.latitude)
  const lng = Number(props.modelValue?.longitude)
  if (Number.isFinite(lat) && Number.isFinite(lng) && lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) {
    placeMarker(lat, lng)
    map?.setView([lat, lng], Math.max(map.getZoom(), 12))
  } else if (marker) {
    marker.remove()
    marker = null
  }
}

watch(() => [props.modelValue?.latitude, props.modelValue?.longitude], syncMarkerFromValue)

onMounted(() => {
  const hasLocation = props.modelValue?.latitude != null && props.modelValue?.longitude != null
  const center = hasLocation
    ? [Number(props.modelValue.latitude), Number(props.modelValue.longitude)]
    : NEPAL_CENTER
  map = L.map(mapEl.value).setView(center, hasLocation ? 13 : 6)
  addBaseTiles(map)
  if (hasLocation) placeMarker(center[0], center[1])
  map.on('click', (e) => setLocation(e.latlng.lat, e.latlng.lng))
})

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
    marker = null
  }
})

// Empty <input type="number"> yields '' — treat that as unset.
function coordOrNull(value) {
  return value === '' || value == null ? null : Number(value)
}

function updateLat(value) {
  emit('update:modelValue', { ...props.modelValue, latitude: coordOrNull(value) })
}

function updateLng(value) {
  emit('update:modelValue', { ...props.modelValue, longitude: coordOrNull(value) })
}
</script>

<template>
  <div>
    <div class="relative">
      <div ref="mapEl" :class="['rounded-xl overflow-hidden border border-gray-200 dark:border-gray-600 z-0', height]"></div>
      <button type="button" @click="useMyLocation" :disabled="locating"
        class="absolute top-3 right-3 z-[500] inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-2 rounded-xl bg-white dark:bg-gray-800 text-secondary dark:text-white shadow-md border border-gray-200 dark:border-gray-600 hover:bg-gray-50 disabled:opacity-60">
        <svg :class="['w-4 h-4', locating ? 'animate-spin' : '']" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="3" stroke-width="2"/><path stroke-linecap="round" stroke-width="2" d="M12 2v3m0 14v3M2 12h3m14 0h3"/>
        </svg>
        {{ locating ? 'Locating…' : 'Use my location' }}
      </button>
    </div>
    <p class="text-xs text-gray-400 dark:text-gray-500 mt-1.5">Click the map to drop the pin, or use your current location.</p>
    <p v-if="locateError" class="field-error">{{ locateError }}</p>
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3 items-end">
      <div>
        <label class="label">Latitude</label>
        <input :value="modelValue?.latitude" type="number" step="any" min="-90" max="90"
          @change="updateLat($event.target.value); syncMarkerFromValue()" class="input-base" placeholder="27.7172" />
      </div>
      <div>
        <label class="label">Longitude</label>
        <input :value="modelValue?.longitude" type="number" step="any" min="-180" max="180"
          @change="updateLng($event.target.value); syncMarkerFromValue()" class="input-base" placeholder="85.3240" />
      </div>
      <button type="button" @click="clearLocation"
        :disabled="modelValue?.latitude == null && modelValue?.longitude == null"
        class="btn-secondary !py-3 text-sm disabled:opacity-50 disabled:cursor-not-allowed">
        Clear location
      </button>
    </div>
  </div>
</template>
