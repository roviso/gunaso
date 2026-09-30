<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { organizationsAPI } from '@/api/organizations'
import { apiErrorMessage } from '@/api/index'
import {
  NEPAL_BOUNDS, addBaseTiles, escapeHtml, pinIcon, dotIcon, haversineKm, formatDistance, loadClusterPlugin,
} from '@/utils/map'

// Public map: every verified organization's head office and branches,
// clustered, searchable and filterable, with "near me" and a direct
// "file a gunaso here" path (branch pins deep-link with their QR code, so
// the case is tagged to that branch exactly as if the QR had been scanned).

const route = useRoute()
const router = useRouter()

const mapEl = ref(null)
const loading = ref(true)
const error = ref(null)
const orgs = ref([])

const search = ref(String(route.query.q || ''))
const activeCategory = ref(String(route.query.category || ''))
const showBranches = ref(true)
const sortBy = ref('name')
const selectedSlug = ref(String(route.query.org || ''))
const userLocation = ref(null)
const locating = ref(false)
const locateError = ref('')
// Mobile: the list and the map share the screen via a toggle.
const mobileView = ref('map')

let map = null
let cluster = null
let userMarker = null
const markersBySlug = new Map() // slug -> [L.Marker]
const hqMarkerBySlug = new Map() // slug -> head-office L.Marker (for the highlight)

// ─── Derived data ────────────────────────────────────────────────────────────

function pointsOf(org) {
  const pts = []
  if (org.latitude != null && org.longitude != null) {
    pts.push({ kind: 'org', latlng: [org.latitude, org.longitude] })
  }
  for (const b of org.branches || []) pts.push({ kind: 'branch', branch: b, latlng: [b.latitude, b.longitude] })
  return pts
}

const categories = computed(() => {
  const counts = {}
  for (const o of orgs.value) if (o.category) counts[o.category] = (counts[o.category] || 0) + 1
  return Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([name, count]) => ({ name, count }))
})

function distanceTo(org) {
  if (!userLocation.value) return null
  const d = pointsOf(org).map((p) => haversineKm(userLocation.value, p.latlng))
  return d.length ? Math.min(...d) : null
}

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  let list = orgs.value.filter((o) => {
    if (activeCategory.value && o.category !== activeCategory.value) return false
    if (!q) return true
    const haystack = [o.name, o.category, o.address, ...(o.branches || []).flatMap((b) => [b.name, b.address])]
      .join(' ').toLowerCase()
    return haystack.includes(q)
  })
  list = list.map((o) => ({ ...o, _distance: distanceTo(o) }))
  if (sortBy.value === 'nearest' && userLocation.value) {
    list.sort((a, b) => (a._distance ?? Infinity) - (b._distance ?? Infinity))
  } else if (sortBy.value === 'resolved') {
    list.sort((a, b) => b.resolved_percent - a.resolved_percent || b.submission_count - a.submission_count)
  } else if (sortBy.value === 'rating') {
    list.sort((a, b) => (b.average_rating ?? -1) - (a.average_rating ?? -1))
  } else {
    list.sort((a, b) => a.name.localeCompare(b.name))
  }
  return list
})

const totalBranches = computed(() => orgs.value.reduce((n, o) => n + (o.branches?.length || 0), 0))

// ─── Popups (all user-supplied text escaped) ────────────────────────────────

function stars(avg) {
  if (avg == null) return '<span style="color:#9ca3af">No public rating yet</span>'
  const full = Math.round(avg)
  return `<span style="color:#f59e0b;letter-spacing:-1px">${'★'.repeat(full)}</span><span style="color:#d1d5db;letter-spacing:-1px">${'★'.repeat(5 - full)}</span> <b>${escapeHtml(avg)}</b>`
}

function popupHtml(org, point) {
  const isBranch = point.kind === 'branch'
  const submitHref = isBranch
    ? `/submit/${encodeURIComponent(org.slug)}?branch=${encodeURIComponent(point.branch.code)}`
    : `/submit/${encodeURIComponent(org.slug)}`
  const where = isBranch ? point.branch.address || point.branch.name : org.address
  const logo = org.logo
    ? `<img src="${escapeHtml(org.logo)}" alt="" style="width:40px;height:40px;border-radius:10px;object-fit:cover;flex-shrink:0">`
    : `<div style="width:40px;height:40px;border-radius:10px;background:#1D3557;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:800;flex-shrink:0">${escapeHtml(org.name[0])}</div>`
  const stat = (label, value) => `<div style="flex:1;text-align:center"><div style="font-weight:800;font-size:15px">${value}</div><div style="font-size:10px;color:#9ca3af;text-transform:uppercase;letter-spacing:.04em">${label}</div></div>`
  return `
    <div style="padding:14px 14px 12px">
      <div style="display:flex;gap:10px;align-items:center">
        ${logo}
        <div style="min-width:0">
          <div style="font-weight:800;font-size:14px;line-height:1.2">${escapeHtml(org.name)}</div>
          <div style="font-size:11px;color:#6b7280;margin-top:2px">${isBranch ? `📍 ${escapeHtml(point.branch.name)} branch` : `🏢 ${escapeHtml(org.category || 'Head office')}`}</div>
        </div>
      </div>
      ${where ? `<div style="font-size:12px;color:#6b7280;margin-top:8px">${escapeHtml(where)}</div>` : ''}
      <div style="font-size:12px;margin-top:8px">${stars(org.average_rating)}</div>
      <div style="display:flex;gap:4px;margin:10px 0;padding:8px 0;border-top:1px solid rgb(156 163 175 / .25);border-bottom:1px solid rgb(156 163 175 / .25)">
        ${stat('Gunaso', escapeHtml(org.submission_count))}
        ${stat('Resolved', `${escapeHtml(org.resolved_percent)}%`)}
        ${stat('Avg days', org.avg_resolution_days != null ? escapeHtml(org.avg_resolution_days) : '—')}
      </div>
      <div style="display:flex;gap:6px">
        <a href="${submitHref}" data-nav style="flex:1;text-align:center;background:#E63946;color:#fff;font-weight:700;font-size:12px;padding:8px 6px;border-radius:10px;text-decoration:none">File a gunaso${isBranch ? ' here' : ''}</a>
        <a href="/organizations/${encodeURIComponent(org.slug)}" data-nav style="flex:1;text-align:center;border:1px solid rgb(156 163 175 / .5);color:inherit;font-weight:600;font-size:12px;padding:8px 6px;border-radius:10px;text-decoration:none">Profile</a>
      </div>
    </div>`
}

// ─── Map lifecycle ───────────────────────────────────────────────────────────

function renderMarkers() {
  if (!cluster) return
  cluster.clearLayers()
  markersBySlug.clear()
  hqMarkerBySlug.clear()
  for (const org of filtered.value) {
    const markers = []
    for (const point of pointsOf(org)) {
      if (point.kind === 'branch' && !showBranches.value) continue
      const icon = point.kind === 'org'
        ? pinIcon({ color: '#E63946', ring: org.slug === selectedSlug.value })
        : dotIcon({ color: '#1D3557' })
      const marker = L.marker(point.latlng, { icon, title: org.name, keyboard: true })
      marker.bindPopup(popupHtml(org, point), { className: 'gmap-popup', maxWidth: 280, minWidth: 260 })
      marker.bindTooltip(escapeHtml(point.kind === 'branch' ? `${org.name} · ${point.branch.name}` : org.name), {
        direction: 'top', offset: [0, point.kind === 'org' ? -4 : -6],
      })
      marker.on('click', () => { selectedSlug.value = org.slug })
      if (point.kind === 'org') hqMarkerBySlug.set(org.slug, marker)
      markers.push(marker)
    }
    if (markers.length) {
      markersBySlug.set(org.slug, markers)
      cluster.addLayers(markers)
    }
  }
}

function focusOrg(org, { openPopup = true } = {}) {
  selectedSlug.value = org.slug
  mobileView.value = 'map'
  const markers = markersBySlug.get(org.slug) || []
  if (!map || !markers.length) return
  nextTick(() => {
    map.invalidateSize()
    if (markers.length === 1) {
      cluster.zoomToShowLayer(markers[0], () => openPopup && markers[0].openPopup())
    } else {
      map.flyToBounds(L.latLngBounds(markers.map((m) => m.getLatLng())), { padding: [60, 60], maxZoom: 14, duration: 0.8 })
      if (openPopup) map.once('moveend', () => cluster.zoomToShowLayer(markers[0], () => markers[0].openPopup()))
    }
  })
}

function fitAll() {
  if (!map) return
  const latlngs = filtered.value.flatMap((o) => pointsOf(o).map((p) => p.latlng))
  if (latlngs.length) map.fitBounds(latlngs, { padding: [50, 50], maxZoom: 13 })
  else map.fitBounds(NEPAL_BOUNDS)
}

function locateMe() {
  if (!navigator.geolocation) {
    locateError.value = 'Your browser does not support location.'
    return
  }
  locating.value = true
  locateError.value = ''
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      locating.value = false
      userLocation.value = [pos.coords.latitude, pos.coords.longitude]
      sortBy.value = 'nearest'
      if (!map) return
      if (userMarker) userMarker.setLatLng(userLocation.value)
      else {
        userMarker = L.circleMarker(userLocation.value, {
          radius: 9, color: '#fff', weight: 3, fillColor: '#2563eb', fillOpacity: 1,
        }).addTo(map).bindTooltip('You are here', { direction: 'top' })
      }
      const nearest = filtered.value[0]
      const target = nearest ? pointsOf(nearest).map((p) => p.latlng) : []
      map.fitBounds([userLocation.value, ...target], { padding: [70, 70], maxZoom: 14 })
    },
    () => {
      locating.value = false
      locateError.value = 'Location permission was denied — search by name or area instead.'
    },
    { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 },
  )
}

// In-popup links are plain <a> tags; route them through the SPA router.
function interceptPopupLinks(e) {
  const a = e.target.closest?.('a[data-nav]')
  if (!a) return
  e.preventDefault()
  router.push(a.getAttribute('href'))
}

async function init() {
  loading.value = true
  error.value = null
  try {
    const [{ data }] = await Promise.all([organizationsAPI.getLocations(), loadClusterPlugin()])
    orgs.value = data
    await nextTick()
    map = L.map(mapEl.value, { zoomControl: false, worldCopyJump: true })
    L.control.zoom({ position: 'bottomright' }).addTo(map)
    addBaseTiles(map)
    map.fitBounds(NEPAL_BOUNDS)
    cluster = L.markerClusterGroup({
      showCoverageOnHover: false,
      maxClusterRadius: 48,
      spiderfyOnMaxZoom: true,
      iconCreateFunction: (c) => {
        const n = c.getChildCount()
        const size = n < 10 ? 36 : n < 50 ? 44 : 52
        return L.divIcon({ html: `<div>${n}</div>`, className: 'gmap-cluster', iconSize: [size, size] })
      },
    })
    map.addLayer(cluster)
    renderMarkers()
    mapEl.value.addEventListener('click', interceptPopupLinks)

    const focused = selectedSlug.value && orgs.value.find((o) => o.slug === selectedSlug.value)
    if (focused) focusOrg(focused)
    else fitAll()
  } catch (err) {
    error.value = apiErrorMessage(err, 'Could not load the map.')
  } finally {
    loading.value = false
  }
}

watch([search, activeCategory, showBranches, sortBy], () => {
  renderMarkers()
  router.replace({
    query: {
      ...(search.value.trim() ? { q: search.value.trim() } : {}),
      ...(activeCategory.value ? { category: activeCategory.value } : {}),
      ...(selectedSlug.value ? { org: selectedSlug.value } : {}),
    },
  })
})

watch(selectedSlug, (slug, prev) => {
  // Swap icons in place — re-rendering the layer would close the popup the
  // user just opened by clicking that very pin.
  hqMarkerBySlug.get(prev)?.setIcon(pinIcon({ color: '#E63946' }))
  hqMarkerBySlug.get(slug)?.setIcon(pinIcon({ color: '#E63946', ring: true }))
})

watch(mobileView, (v) => {
  if (v === 'map') nextTick(() => map?.invalidateSize())
})

onMounted(init)

onBeforeUnmount(() => {
  mapEl.value?.removeEventListener('click', interceptPopupLinks)
  if (map) {
    map.remove()
    map = null
    cluster = null
    userMarker = null
  }
})
</script>

<template>
  <div class="relative h-[calc(100vh-4rem)] h-[calc(100dvh-4rem)] flex bg-app-bg dark:bg-gray-900 overflow-hidden">
    <!-- ── Sidebar / list ─────────────────────────────────────────────── -->
    <aside
      :class="['w-full md:w-[380px] lg:w-[400px] shrink-0 flex-col bg-white dark:bg-gray-800 border-r border-gray-100 dark:border-gray-700 z-10',
        mobileView === 'list' ? 'flex' : 'hidden md:flex']">
      <div class="p-4 sm:p-5 border-b border-gray-100 dark:border-gray-700 space-y-3">
        <div class="flex items-end justify-between gap-2">
          <div>
            <h1 class="font-display font-bold text-xl text-secondary dark:text-white leading-tight">Find an office</h1>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5" aria-live="polite">
              <template v-if="loading">Loading the map…</template>
              <template v-else>{{ orgs.length }} organizations · {{ totalBranches }} branches</template>
            </p>
          </div>
          <button type="button" @click="locateMe" :disabled="locating"
            class="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-2 rounded-xl bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-200 hover:bg-blue-100 disabled:opacity-60">
            <svg :class="['w-4 h-4', locating ? 'animate-spin' : '']" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="12" r="3" stroke-width="2"/><path stroke-linecap="round" stroke-width="2" d="M12 2v3m0 14v3M2 12h3m14 0h3"/>
            </svg>
            {{ locating ? 'Locating…' : 'Near me' }}
          </button>
        </div>
        <p v-if="locateError" class="text-xs text-amber-600 dark:text-amber-400">{{ locateError }}</p>

        <div class="relative">
          <svg class="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
          </svg>
          <label for="map-search" class="sr-only">Search organizations, branches or areas</label>
          <input id="map-search" v-model="search" type="search" placeholder="Organization, branch or area…" class="input-base !pl-10 !py-2.5" />
        </div>

        <div v-if="categories.length > 1" class="flex gap-1.5 overflow-x-auto pb-1 -mx-1 px-1 scrollbar-none">
          <button type="button" @click="activeCategory = ''"
            :class="['shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors',
              !activeCategory ? 'bg-secondary text-white border-secondary' : 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-gray-300']">
            All
          </button>
          <button v-for="c in categories" :key="c.name" type="button" @click="activeCategory = activeCategory === c.name ? '' : c.name"
            :class="['shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold border capitalize transition-colors',
              activeCategory === c.name ? 'bg-secondary text-white border-secondary' : 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-gray-300']">
            {{ c.name }} <span class="opacity-60">{{ c.count }}</span>
          </button>
        </div>

        <div class="flex items-center justify-between gap-3 text-xs">
          <label class="inline-flex items-center gap-2 font-medium text-gray-600 dark:text-gray-300 cursor-pointer">
            <input v-model="showBranches" type="checkbox" class="rounded border-gray-300 text-primary focus:ring-primary/30" />
            Show branches
          </label>
          <label class="inline-flex items-center gap-1.5 text-gray-500 dark:text-gray-400">
            Sort
            <select v-model="sortBy" class="rounded-lg border-gray-200 dark:border-gray-600 dark:bg-gray-800 text-xs py-1 pl-2 pr-7">
              <option value="name">A–Z</option>
              <option value="nearest" :disabled="!userLocation">Nearest</option>
              <option value="resolved">Most resolved</option>
              <option value="rating">Best rated</option>
            </select>
          </label>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto">
        <div v-if="loading" class="p-4 space-y-3">
          <div v-for="i in 5" :key="i" class="flex gap-3 p-3"><div class="skeleton w-11 h-11" /><div class="flex-1 space-y-2"><div class="skeleton h-3.5 w-2/3" /><div class="skeleton h-3 w-1/3" /></div></div>
        </div>
        <div v-else-if="error" class="p-6 text-center text-sm text-red-500">{{ error }}
          <button class="block mx-auto mt-3 btn-secondary !py-2 text-xs" @click="init">Try again</button>
        </div>
        <div v-else-if="!orgs.length" class="p-8 text-center">
          <p class="font-semibold text-gray-700 dark:text-gray-200">No organizations on the map yet</p>
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Organizations appear here once they add their location.</p>
          <RouterLink to="/organizations" class="btn-secondary !py-2 text-sm mt-4">Browse the directory</RouterLink>
        </div>
        <div v-else-if="!filtered.length" class="p-8 text-center text-sm text-gray-500 dark:text-gray-400">
          Nothing matches “{{ search }}”.
          <button class="block mx-auto mt-2 text-primary font-semibold hover:underline" @click="search = ''; activeCategory = ''">Clear filters</button>
        </div>
        <ul v-else class="divide-y divide-gray-100 dark:divide-gray-700/70">
          <li v-for="org in filtered" :key="org.slug">
            <div role="button" tabindex="0" @click="focusOrg(org)" @keydown.enter="focusOrg(org)"
              :class="['w-full text-left px-4 sm:px-5 py-3.5 flex gap-3 cursor-pointer transition-colors outline-none focus-visible:bg-primary/5',
                selectedSlug === org.slug ? 'bg-primary/[0.06] dark:bg-primary/10' : 'hover:bg-gray-50 dark:hover:bg-gray-700/40']">
              <img v-if="org.logo" :src="org.logo" alt="" class="w-11 h-11 rounded-xl object-cover shrink-0" loading="lazy" />
              <div v-else class="w-11 h-11 rounded-xl bg-secondary/10 dark:bg-gray-700 text-secondary dark:text-white font-bold flex items-center justify-center shrink-0">
                {{ org.name[0] }}
              </div>
              <div class="min-w-0 flex-1">
                <div class="flex items-start justify-between gap-2">
                  <p class="font-semibold text-sm text-gray-900 dark:text-white leading-snug">{{ org.name }}</p>
                  <span v-if="org._distance != null" class="text-[11px] font-semibold text-blue-600 dark:text-blue-300 shrink-0">{{ formatDistance(org._distance) }}</span>
                </div>
                <p class="text-xs text-gray-500 dark:text-gray-400 capitalize">{{ org.category }}<span v-if="org.branches?.length"> · {{ org.branches.length }} branch{{ org.branches.length === 1 ? '' : 'es' }}</span></p>
                <div class="flex items-center gap-3 mt-1.5 text-[11px] text-gray-500 dark:text-gray-400">
                  <span v-if="org.average_rating != null" class="font-semibold text-amber-600 dark:text-amber-400">★ {{ org.average_rating }}</span>
                  <span v-if="org.submission_count"><b class="text-gray-700 dark:text-gray-200">{{ org.resolved_percent }}%</b> resolved</span>
                  <span v-if="org.avg_resolution_days != null">~{{ org.avg_resolution_days }}d to resolve</span>
                </div>
                <div v-if="selectedSlug === org.slug" class="flex gap-2 mt-2.5">
                  <RouterLink :to="`/submit/${org.slug}`" class="text-xs font-bold text-white bg-primary hover:bg-primary-600 px-3 py-1.5 rounded-lg" @click.stop>File a gunaso</RouterLink>
                  <RouterLink :to="`/organizations/${org.slug}`" class="text-xs font-semibold text-secondary dark:text-gray-200 border border-gray-200 dark:border-gray-600 px-3 py-1.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700" @click.stop>Profile</RouterLink>
                </div>
              </div>
            </div>
          </li>
        </ul>
      </div>
    </aside>

    <!-- ── Map ───────────────────────────────────────────────────────── -->
    <section :class="['relative flex-1 min-w-0', mobileView === 'map' ? 'block' : 'hidden md:block']" aria-label="Map of organizations">
      <div ref="mapEl" class="absolute inset-0 z-0" />

      <!-- Legend -->
      <div class="absolute left-3 top-3 md:top-auto md:bottom-3 z-[500] card !rounded-xl px-3 py-2 text-[11px] text-gray-600 dark:text-gray-300 flex items-center gap-3 shadow-lg">
        <span class="inline-flex items-center gap-1.5"><svg width="10" height="14" viewBox="0 0 30 42" aria-hidden="true"><path d="M15 0C6.7 0 0 6.7 0 15c0 11.2 15 27 15 27s15-15.8 15-27C30 6.7 23.3 0 15 0z" fill="#E63946"/></svg>Head office</span>
        <span class="inline-flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-secondary ring-2 ring-white" />Branch</span>
        <button class="font-semibold text-primary hover:underline" @click="fitAll">Show all</button>
      </div>

      <div v-if="loading" class="absolute inset-0 z-[400] flex items-center justify-center bg-app-bg/60 dark:bg-gray-900/60 backdrop-blur-[1px]">
        <div class="card px-4 py-3 text-sm text-gray-600 dark:text-gray-300 flex items-center gap-2">
          <svg class="w-4 h-4 animate-spin text-primary" fill="none" viewBox="0 0 24 24" aria-hidden="true"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
          Loading map…
        </div>
      </div>
    </section>

    <!-- Mobile list/map toggle -->
    <div class="md:hidden fixed bottom-5 left-1/2 -translate-x-1/2 z-[600] flex rounded-full bg-secondary text-white shadow-xl p-1">
      <button v-for="v in ['map', 'list']" :key="v" @click="mobileView = v"
        :class="['px-5 py-2 rounded-full text-sm font-semibold capitalize transition-colors', mobileView === v ? 'bg-white text-secondary' : 'text-white/80']">
        {{ v }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.scrollbar-none { scrollbar-width: none; }
.scrollbar-none::-webkit-scrollbar { display: none; }
</style>
