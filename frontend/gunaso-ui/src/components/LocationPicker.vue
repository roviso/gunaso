<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

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
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(map)
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
    <div ref="mapEl" :class="['rounded-xl overflow-hidden border border-gray-200 dark:border-gray-600 z-0', height]"></div>
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
