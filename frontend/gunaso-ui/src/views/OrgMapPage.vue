<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useAuthStore } from '@/stores/auth'
import { useOrganizationStore } from '@/stores/organization'
import { submissionsAPI } from '@/api/submissions'
import { apiErrorMessage } from '@/api/index'
import { NEPAL_CENTER, addBaseTiles, escapeHtml } from '@/utils/map'

// Branch hotspot map: every located branch sized by volume and coloured by
// how much is still open / overdue, for a chosen time window, plus the live
// "thinking bubble" feed of recent gunaso excerpts.

const authStore = useAuthStore()
const orgStore = useOrganizationStore()

const canView = computed(() => authStore.hasPrivilege('view_submissions'))
const canManageProfile = computed(() => authStore.hasPrivilege('manage_org_profile'))
const canManageBranches = computed(() => authStore.hasPrivilege('manage_branches'))

const missingOrgLocation = computed(() => {
  const org = orgStore.currentOrg
  return !!org && (org.latitude == null || org.longitude == null)
})

const WINDOWS = [
  { value: '7', label: '7 days' },
  { value: '30', label: '30 days' },
  { value: '90', label: '90 days' },
  { value: '', label: 'All time' },
]
const windowDays = ref('30')
const liveFeed = ref(true)

const loading = ref(true)
const loadError = ref('')
const branches = ref([])
const recent = ref([])
const unlinkedCount = ref(0)
const selectedBranchId = ref(null)

const mapEl = ref(null)
let map = null
const layers = new Map() // branch id -> L.Marker
let bubbleTimer = null
let currentPopup = null

const prefersReducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false

const TYPE_META = {
  complaint: { icon: '⚠️', label: 'Complaint' },
  feedback: { icon: '💬', label: 'Feedback' },
  suggestion: { icon: '💡', label: 'Suggestion' },
}

const totals = computed(() => branches.value.reduce((t, b) => ({
  submissions: t.submissions + b.submission_count,
  open: t.open + b.open_count,
  overdue: t.overdue + b.overdue_count,
  resolved: t.resolved + b.resolved_count,
}), { submissions: 0, open: 0, overdue: 0, resolved: 0 }))

const ranked = computed(() =>
  [...branches.value].sort((a, b) => b.overdue_count - a.overdue_count || b.open_count - a.open_count || b.submission_count - a.submission_count)
)
const maxCount = computed(() => Math.max(1, ...branches.value.map((b) => b.submission_count)))

function health(b) {
  if (b.overdue_count > 0) return { color: '#dc2626', label: 'Overdue cases', tone: 'text-red-600 dark:text-red-400' }
  if (b.open_count > 0) return { color: '#f59e0b', label: 'Open cases', tone: 'text-amber-600 dark:text-amber-400' }
  if (b.submission_count > 0) return { color: '#16a34a', label: 'All handled', tone: 'text-green-600 dark:text-green-400' }
  return { color: '#64748b', label: 'Quiet', tone: 'text-gray-500' }
}

function hotspotIcon(b, selected) {
  const size = Math.round(26 + 34 * Math.sqrt(b.submission_count / maxCount.value))
  const { color } = health(b)
  const pulse = b.overdue_count > 0 && !prefersReducedMotion
    ? `<span class="pulse" style="background:${color}"></span>` : ''
  return L.divIcon({
    className: 'gmap-hotspot',
    html: `<div style="position:relative;width:${size}px;height:${size}px">
      ${pulse}
      <span style="background:${color};opacity:.9;border:3px solid ${selected ? '#1D3557' : '#fff'};box-shadow:0 4px 12px rgb(15 31 56 / .35);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:800;font-size:${size > 40 ? 14 : 12}px">${escapeHtml(b.submission_count)}</span>
    </div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
    tooltipAnchor: [0, -size / 2],
  })
}

function branchTooltip(b) {
  return `<div style="min-width:150px">
    <div style="font-weight:700">${escapeHtml(b.name)}</div>
    <div style="font-size:11px;margin-top:3px">${escapeHtml(b.open_count)} open · ${escapeHtml(b.overdue_count)} overdue · ${escapeHtml(b.resolved_count)} resolved</div>
  </div>`
}

function renderBranches() {
  if (!map) return
  layers.forEach((m) => m.remove())
  layers.clear()
  for (const b of branches.value) {
    const marker = L.marker([b.latitude, b.longitude], {
      icon: hotspotIcon(b, b.id === selectedBranchId.value), keyboard: true, title: b.name,
    }).addTo(map)
    marker.bindTooltip(branchTooltip(b), { direction: 'top' })
    marker.on('click', () => selectBranch(b.id, false))
    layers.set(b.id, marker)
  }
}

function fitToBranches() {
  if (!map) return
  if (branches.value.length) {
    map.fitBounds(branches.value.map((b) => [b.latitude, b.longitude]), { padding: [50, 50], maxZoom: 15 })
  } else {
    map.setView(NEPAL_CENTER, 7)
  }
}

function selectBranch(id, fly = true) {
  const prev = selectedBranchId.value
  selectedBranchId.value = prev === id ? null : id
  for (const bid of [prev, id]) {
    const b = branches.value.find((x) => x.id === bid)
    if (b) layers.get(bid)?.setIcon(hotspotIcon(b, bid === selectedBranchId.value))
  }
  const b = branches.value.find((x) => x.id === id)
  if (fly && b && selectedBranchId.value) map?.flyTo([b.latitude, b.longitude], Math.max(map.getZoom(), 14), { duration: 0.6 })
}

const visibleRecent = computed(() =>
  selectedBranchId.value ? recent.value.filter((r) => r.branch_id === selectedBranchId.value) : recent.value
)

function showBubble(entry) {
  const marker = layers.get(entry.branch_id)
  if (!marker || !map) return
  const meta = TYPE_META[entry.type] || { icon: '📋', label: entry.type }
  if (currentPopup) map.closePopup(currentPopup)
  // Excerpts are citizen-written — escape everything interpolated here.
  const popup = L.popup({
    closeButton: false, autoClose: false, closeOnClick: false, autoPan: false,
    className: 'thought-bubble-popup', offset: [0, -8],
  })
    .setLatLng(marker.getLatLng())
    .setContent(`
      <div class="animate-thought-bubble bg-white dark:bg-gray-800 rounded-2xl rounded-bl-sm shadow-lg border border-gray-100 dark:border-gray-700 px-3 py-2 max-w-[220px]">
        <p class="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-1">${meta.icon} ${escapeHtml(meta.label)}</p>
        <p class="text-sm text-gray-800 dark:text-white leading-snug">${escapeHtml(entry.excerpt)}</p>
      </div>`)
    .openOn(map)
  currentPopup = popup
  setTimeout(() => {
    if (currentPopup === popup) {
      map?.closePopup(popup)
      currentPopup = null
    }
  }, 5800)
}

function stopBubbles() {
  if (bubbleTimer) clearTimeout(bubbleTimer)
  bubbleTimer = null
  if (currentPopup && map) map.closePopup(currentPopup)
  currentPopup = null
}

function startBubbles() {
  stopBubbles()
  if (prefersReducedMotion || !liveFeed.value || !recent.value.length) return
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
    const { data } = await submissionsAPI.mapFeed(windowDays.value ? { days: windowDays.value } : {})
    branches.value = data.branches
    recent.value = data.recent
    unlinkedCount.value = data.unlinked_count
  } catch (err) {
    loadError.value = apiErrorMessage(err, 'Could not load the map feed.')
  } finally {
    loading.value = false
  }
}

async function refresh({ refit = false } = {}) {
  await loadFeed()
  await nextTick()
  if (!mapEl.value || loadError.value) return
  if (!map) {
    map = L.map(mapEl.value, { zoomControl: false })
    L.control.zoom({ position: 'bottomright' }).addTo(map)
    addBaseTiles(map)
    refit = true
  }
  renderBranches()
  if (refit) fitToBranches()
  startBubbles()
}

watch(windowDays, () => refresh())
watch(liveFeed, (on) => (on ? startBubbles() : stopBubbles()))

function timeAgo(d) {
  const mins = Math.round((Date.now() - new Date(d).getTime()) / 60000)
  if (mins < 60) return `${Math.max(1, mins)}m ago`
  const hours = Math.round(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.round(hours / 24)}d ago`
}

onMounted(async () => {
  if (!orgStore.currentOrg && authStore.accessibleOrgSlug) {
    await orgStore.fetchOrgBySlug(authStore.accessibleOrgSlug)
  }
  if (!canView.value) return
  await refresh({ refit: true })
})

onBeforeUnmount(() => {
  stopBubbles()
  if (map) {
    map.remove()
    map = null
  }
})
</script>

<template>
  <div class="p-4 sm:p-6 space-y-5">
    <div class="flex items-start justify-between gap-4 flex-wrap">
      <div>
        <h1 class="text-xl font-extrabold text-secondary dark:text-white">Branch hotspots</h1>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
          Where your gunaso come from, and where they're piling up. Bigger = more cases; red = overdue.
        </p>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <div class="flex p-1 rounded-xl bg-gray-100 dark:bg-gray-800" role="tablist" aria-label="Time window">
          <button v-for="w in WINDOWS" :key="w.value" role="tab" :aria-selected="windowDays === w.value" @click="windowDays = w.value"
            :class="['px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors',
              windowDays === w.value ? 'bg-white dark:bg-gray-700 text-secondary dark:text-white shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700']">
            {{ w.label }}
          </button>
        </div>
        <label class="inline-flex items-center gap-2 text-xs font-semibold text-gray-600 dark:text-gray-300 cursor-pointer select-none">
          <input v-model="liveFeed" type="checkbox" class="rounded border-gray-300 text-primary focus:ring-primary/30" />
          Live bubbles
        </label>
      </div>
    </div>

    <div v-if="missingOrgLocation"
      class="flex items-start gap-3 p-4 rounded-2xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50 text-sm text-amber-800 dark:text-amber-200">
      <svg class="w-5 h-5 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
      </svg>
      <p>
        Your head office has no location yet. Citizens can still find you on the
        <RouterLink to="/map" class="font-semibold underline hover:no-underline">public map</RouterLink> through your located branches,
        <template v-if="canManageProfile">but setting it in <RouterLink to="/org/settings" class="font-semibold underline hover:no-underline">Settings</RouterLink> helps.</template>
        <template v-else>but your admin can add it in Settings.</template>
      </p>
    </div>

    <div v-if="!canView" class="card p-6 text-sm text-gray-600 dark:text-gray-300">
      You don't have permission to view submissions for this organization.
    </div>

    <template v-else>
      <!-- Summary -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div v-for="card in [
          { label: 'Branch-linked gunaso', value: totals.submissions, tone: 'text-secondary dark:text-white' },
          { label: 'Still open', value: totals.open, tone: 'text-amber-600 dark:text-amber-400' },
          { label: 'Overdue', value: totals.overdue, tone: 'text-red-600 dark:text-red-400' },
          { label: 'Not linked to a branch', value: unlinkedCount, tone: 'text-gray-600 dark:text-gray-300' },
        ]" :key="card.label" class="card p-4">
          <p class="text-[11px] font-semibold uppercase tracking-wide text-gray-400">{{ card.label }}</p>
          <p :class="['text-2xl font-extrabold mt-1', card.tone]">
            <span v-if="loading" class="skeleton inline-block h-7 w-12 align-middle" />
            <template v-else>{{ card.value }}</template>
          </p>
        </div>
      </div>
      <p v-if="!loading && unlinkedCount > 0 && totals.submissions < unlinkedCount" class="text-xs text-gray-500 dark:text-gray-400 -mt-2">
        Most gunaso aren't tied to a branch yet — put each branch's QR code at its counter so cases land on the right pin.
        <RouterLink v-if="canManageBranches" to="/org/branches" class="text-primary font-semibold hover:underline">Branch QR codes →</RouterLink>
      </p>

      <div v-if="loadError" class="card p-6 text-center text-sm text-red-500 dark:text-red-400">
        {{ loadError }}
        <button class="block mx-auto mt-3 btn-secondary !py-2 text-xs" @click="refresh({ refit: true })">Try again</button>
      </div>

      <div v-else-if="!loading && !branches.length" class="card p-10 text-center">
        <p class="font-semibold text-gray-700 dark:text-gray-200">No branches on the map yet</p>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Add a branch with a location under
          <RouterLink to="/org/branches" class="text-primary hover:underline font-medium">Branches</RouterLink>
          to see it here.
        </p>
      </div>

      <div v-else class="grid grid-cols-1 xl:grid-cols-[1fr,360px] gap-5">
        <div class="relative self-start">
          <div ref="mapEl" class="h-[460px] sm:h-[560px] rounded-2xl overflow-hidden border border-gray-100 dark:border-gray-700 z-0" />
          <div class="absolute left-3 bottom-3 z-[500] card !rounded-xl px-3 py-2 text-[11px] text-gray-600 dark:text-gray-300 flex items-center gap-3 shadow-lg">
            <span class="inline-flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-red-600" />Overdue</span>
            <span class="inline-flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-amber-500" />Open</span>
            <span class="inline-flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-green-600" />Handled</span>
            <button class="font-semibold text-primary hover:underline" @click="fitToBranches">Fit</button>
          </div>
        </div>

        <div class="space-y-5">
          <!-- Branch leaderboard -->
          <div class="card p-4">
            <h2 class="text-sm font-bold text-gray-800 dark:text-white mb-3">Branches needing attention</h2>
            <ul class="space-y-1 max-h-[260px] overflow-y-auto -mx-1 px-1">
              <li v-for="b in ranked" :key="b.id">
                <button @click="selectBranch(b.id)"
                  :class="['w-full text-left p-2.5 rounded-xl transition-colors',
                    selectedBranchId === b.id ? 'bg-primary/[0.07] ring-1 ring-primary/30' : 'hover:bg-gray-50 dark:hover:bg-gray-700/40']">
                  <div class="flex items-center justify-between gap-2">
                    <span class="text-sm font-semibold text-gray-800 dark:text-gray-100 truncate">{{ b.name }}</span>
                    <span :class="['text-[11px] font-bold shrink-0', health(b).tone]">{{ health(b).label }}</span>
                  </div>
                  <div class="mt-1.5 h-1.5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden flex" :title="`${b.resolved_count} resolved · ${b.open_count} open`">
                    <span class="bg-green-500" :style="{ width: `${(b.resolved_count / maxCount) * 100}%` }" />
                    <span class="bg-amber-400" :style="{ width: `${((b.open_count - b.overdue_count) / maxCount) * 100}%` }" />
                    <span class="bg-red-500" :style="{ width: `${(b.overdue_count / maxCount) * 100}%` }" />
                  </div>
                  <p class="text-[11px] text-gray-500 dark:text-gray-400 mt-1">
                    {{ b.submission_count }} total · {{ b.open_count }} open · {{ b.overdue_count }} overdue ·
                    ⚠️ {{ b.by_type.complaint }} 💬 {{ b.by_type.feedback }} 💡 {{ b.by_type.suggestion }}
                  </p>
                </button>
                <div v-if="selectedBranchId === b.id" class="flex gap-2 px-2.5 pb-2 pt-1">
                  <RouterLink :to="{ name: 'OrgSubmissions', query: { branch: String(b.id) } }" class="text-xs font-bold text-primary hover:underline">View its submissions →</RouterLink>
                  <RouterLink v-if="b.overdue_count" :to="{ name: 'OrgSubmissions', query: { branch: String(b.id), queue: 'overdue' } }" class="text-xs font-bold text-red-600 hover:underline">Overdue only →</RouterLink>
                </div>
              </li>
            </ul>
          </div>

          <!-- Recent feed (also the accessible / reduced-motion fallback for the bubbles) -->
          <div class="card p-4">
            <div class="flex items-center justify-between mb-3">
              <h2 class="text-sm font-bold text-gray-800 dark:text-white">Recent gunaso</h2>
              <button v-if="selectedBranchId" class="text-xs text-primary font-semibold hover:underline" @click="selectBranch(selectedBranchId, false)">Show all</button>
            </div>
            <div v-if="!visibleRecent.length" class="text-sm text-gray-400 dark:text-gray-500 text-center py-6">
              Nothing in this window.
            </div>
            <ul v-else class="space-y-2 max-h-[240px] overflow-y-auto">
              <li v-for="entry in visibleRecent" :key="entry.reference_number">
                <RouterLink :to="{ name: 'OrgSubmissions', query: { ref: entry.reference_number } }"
                  class="block p-2.5 rounded-xl bg-gray-50 dark:bg-gray-700/40 hover:bg-gray-100 dark:hover:bg-gray-700/70 transition-colors">
                  <p class="text-[11px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide flex justify-between gap-2">
                    <span class="truncate">{{ TYPE_META[entry.type]?.icon || '📋' }} {{ branches.find((b) => b.id === entry.branch_id)?.name || 'Branch' }}</span>
                    <span class="normal-case font-medium shrink-0">{{ timeAgo(entry.created_at) }}</span>
                  </p>
                  <p class="text-sm text-gray-800 dark:text-gray-200 mt-0.5">{{ entry.excerpt }}</p>
                </RouterLink>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style>
/* Global (not scoped) — Leaflet renders these outside Vue's component tree. */
.thought-bubble-popup .leaflet-popup-content-wrapper { background: transparent; box-shadow: none; padding: 0; }
.thought-bubble-popup .leaflet-popup-content { margin: 0; }
.thought-bubble-popup .leaflet-popup-tip-container { display: none; }
</style>
