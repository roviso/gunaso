<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import L from 'leaflet'
import { organizationsAPI } from '@/api/organizations'
import { NEPAL_BOUNDS, addBaseTiles, pinIcon, dotIcon, escapeHtml } from '@/utils/map'

// A live, read-only glimpse of the public map for the landing page. The
// locations payload is only fetched (and the map only built) once the
// section scrolls into view, so the hero stays fast.
const emit = defineEmits(['loaded'])
const router = useRouter()
const root = ref(null)
const mapEl = ref(null)
const state = ref('idle') // idle | loading | ready | empty | error
let map = null
let observer = null

async function boot() {
  state.value = 'loading'
  try {
    const [{ data }] = await Promise.all([
      organizationsAPI.getLocations(),
      import('leaflet/dist/leaflet.css'),
    ])
    const points = []
    for (const org of data) {
      if (org.latitude != null) points.push({ org, latlng: [org.latitude, org.longitude], hq: true })
      for (const b of org.branches || []) points.push({ org, latlng: [b.latitude, b.longitude], hq: false, branch: b })
    }
    emit('loaded', { organizations: data.length, points: points.length })
    if (!points.length) {
      state.value = 'empty'
      return
    }
    map = L.map(mapEl.value, {
      zoomControl: false, scrollWheelZoom: false, dragging: !L.Browser.mobile,
      doubleClickZoom: false, boxZoom: false, keyboard: false, attributionControl: true,
    })
    addBaseTiles(map)
    for (const p of points) {
      L.marker(p.latlng, { icon: p.hq ? pinIcon({ size: 24 }) : dotIcon({ size: 12 }) })
        .addTo(map)
        .bindTooltip(escapeHtml(p.hq ? p.org.name : `${p.org.name} · ${p.branch.name}`), { direction: 'top' })
        .on('click', () => router.push({ name: 'OrganizationsMap', query: { org: p.org.slug } }))
    }
    map.fitBounds(points.length > 1 ? points.map((p) => p.latlng) : NEPAL_BOUNDS, { padding: [40, 40], maxZoom: 12 })
    state.value = 'ready'
  } catch {
    state.value = 'error'
  }
}

onMounted(() => {
  if (!('IntersectionObserver' in window)) return boot()
  observer = new IntersectionObserver((entries) => {
    if (entries.some((e) => e.isIntersecting)) {
      observer.disconnect()
      boot()
    }
  }, { rootMargin: '200px' })
  observer.observe(root.value)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  map?.remove()
  map = null
})
</script>

<template>
  <div ref="root" class="relative w-full h-full min-h-[320px] rounded-3xl overflow-hidden bg-secondary/5 dark:bg-gray-800">
    <div ref="mapEl" class="absolute inset-0 z-0" />
    <div v-if="state !== 'ready'" class="absolute inset-0 flex items-center justify-center">
      <!-- Decorative placeholder: dotted terrain + pins, until real data arrives -->
      <div class="absolute inset-0 opacity-[0.12] dark:opacity-[0.18]"
        style="background-image: radial-gradient(#1D3557 1.4px, transparent 1.4px); background-size: 18px 18px;" />
      <p class="relative text-sm font-medium text-gray-500 dark:text-gray-400">
        <template v-if="state === 'empty'">Organizations appear here as they add their offices.</template>
        <template v-else-if="state === 'error'">The map preview couldn't load.</template>
        <template v-else>Loading map…</template>
      </p>
    </div>
  </div>
</template>
