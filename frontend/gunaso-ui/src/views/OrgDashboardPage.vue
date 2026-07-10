<script setup>
import { computed, ref, onMounted } from 'vue'
import { useSubmissionStore } from '@/stores/submission'
import { useOrganizationStore } from '@/stores/organization'
import { useAuthStore } from '@/stores/auth'
import StatsCard from '@/components/StatsCard.vue'
import TrendChart from '@/components/TrendChart.vue'
import StatusDonut from '@/components/StatusDonut.vue'
import ActivityFeed from '@/components/ActivityFeed.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import PriorityBadge from '@/components/PriorityBadge.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const submissionStore = useSubmissionStore()
const orgStore = useOrganizationStore()
const authStore = useAuthStore()

const lastUpdated = ref(null)
const refreshing = ref(false)

// Convenience alias for the stats object (see services.py::organization_stats)
const s = computed(() => submissionStore.orgStats || {})

const loadError = computed(() => submissionStore.statsError || submissionStore.error)
const isEmpty = computed(
  () => !submissionStore.loading && submissionStore.orgStats && (s.value.total ?? 0) === 0
)

function formatDayLabel(isoDate) {
  return new Date(isoDate + 'T00:00:00').toLocaleDateString('en-US', {
    month: 'short', day: 'numeric',
  })
}

// 7-day trend from the stats endpoint; derived from loaded submissions as fallback
const trendData = computed(() => {
  if (Array.isArray(s.value.trend)) {
    return s.value.trend.map((d) => ({ label: formatDayLabel(d.date), count: d.count }))
  }
  const now = new Date()
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(now)
    d.setDate(d.getDate() - (6 - i))
    const dateStr = d.toISOString().slice(0, 10)
    const count = submissionStore.orgSubmissions.filter((sub) =>
      sub.created_at?.startsWith(dateStr)
    ).length
    return { label: formatDayLabel(dateStr), count }
  })
})

const statusBreakdown = computed(() => {
  if (s.value.by_status && typeof s.value.by_status === 'object') return s.value.by_status
  const result = {}
  for (const sub of submissionStore.orgSubmissions) {
    result[sub.status] = (result[sub.status] || 0) + 1
  }
  return result
})

const resolutionRate = computed(() => {
  const total = s.value.total ?? 0
  if (!total) return null
  const done = (statusBreakdown.value.resolved || 0) + (statusBreakdown.value.closed || 0)
  return Math.round((done / total) * 100)
})

// ── Needs attention: active submissions, most urgent + oldest first ──────────
const ACTIVE_STATUSES = new Set(['submitted', 'acknowledged', 'in_review', 'escalated'])
const PRIORITY_ORDER = { urgent: 0, high: 1, medium: 2, low: 3 }

const needsAttention = computed(() =>
  submissionStore.orgSubmissions
    .filter((sub) => ACTIVE_STATUSES.has(sub.status))
    .sort((a, b) => {
      const p = (PRIORITY_ORDER[a.priority] ?? 9) - (PRIORITY_ORDER[b.priority] ?? 9)
      if (p !== 0) return p
      return new Date(a.created_at) - new Date(b.created_at)
    })
    .slice(0, 6)
)

function ageDays(dateStr) {
  const days = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000)
  if (days < 1) return 'today'
  return days === 1 ? '1 day' : `${days} days`
}

// ── Type / priority breakdown bars ────────────────────────────────────────────
const TYPE_META = [
  { key: 'complaint', label: 'Complaints', icon: '⚠️', bar: 'bg-red-400' },
  { key: 'feedback', label: 'Feedback', icon: '💬', bar: 'bg-blue-400' },
  { key: 'suggestion', label: 'Suggestions', icon: '💡', bar: 'bg-emerald-400' },
]
const PRIORITY_META = [
  { key: 'urgent', label: 'Urgent', bar: 'bg-red-500' },
  { key: 'high', label: 'High', bar: 'bg-orange-400' },
  { key: 'medium', label: 'Medium', bar: 'bg-blue-400' },
  { key: 'low', label: 'Low', bar: 'bg-gray-300 dark:bg-gray-600' },
]

function breakdownRows(meta, source) {
  const data = source || {}
  const max = Math.max(1, ...meta.map((m) => data[m.key] || 0))
  return meta.map((m) => ({
    ...m,
    count: data[m.key] || 0,
    width: `${Math.round(((data[m.key] || 0) / max) * 100)}%`,
  }))
}

const typeRows = computed(() => breakdownRows(TYPE_META, s.value.by_type))
const priorityRows = computed(() => breakdownRows(PRIORITY_META, s.value.by_priority))

// ── Recent activity ───────────────────────────────────────────────────────────
// Timeline entries are serialized as {status, note, created_at, updated_by};
// normalize to the shape ActivityFeed renders.
const recentActivity = computed(() => {
  const fromTimelines = submissionStore.orgSubmissions.flatMap((sub) =>
    (sub.timeline || []).map((t) => ({
      new_status: t.status || t.new_status,
      note: t.note,
      created_at: t.created_at,
      updated_by_name: t.updated_by,
      reference: sub.reference_number,
    }))
  )
  if (fromTimelines.length) {
    return fromTimelines
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      .slice(0, 8)
  }
  // Fallback: last 5 events included in the stats payload
  return (s.value.recent_activity || []).map((u) => ({
    new_status: u.new_status,
    note: u.note,
    created_at: u.timestamp,
    updated_by_name: u.updated_by,
    reference: u.reference,
  }))
})

async function loadData() {
  await Promise.all([
    submissionStore.fetchOrgSubmissions({ page_size: 100 }),
    submissionStore.fetchOrgStats(),
  ])
  lastUpdated.value = new Date()
}

async function refresh() {
  refreshing.value = true
  try {
    await loadData()
  } finally {
    refreshing.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <div class="p-6 space-y-6">
    <!-- Page header -->
    <div class="flex items-start justify-between gap-4 flex-wrap">
      <div>
        <h1 class="text-xl font-extrabold text-secondary dark:text-white">Dashboard</h1>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
          Overview for
          <span class="font-semibold text-gray-700 dark:text-gray-200">
            {{ orgStore.currentOrg?.name || authStore.user?.organization_name || 'your organization' }}
          </span>
        </p>
      </div>

      <div class="flex items-center gap-3">
        <span v-if="lastUpdated" class="text-xs text-gray-400 dark:text-gray-500 hidden sm:block">
          Updated {{ lastUpdated.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) }}
        </span>
        <button
          @click="refresh"
          :disabled="refreshing"
          class="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium text-gray-600 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50">
          <svg :class="['w-4 h-4', refreshing && 'animate-spin']" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
          Refresh
        </button>
      </div>
    </div>

    <!-- Error state with retry -->
    <div v-if="loadError && !submissionStore.orgStats"
      class="card p-6 border-red-200 dark:border-red-900/50 bg-red-50/50 dark:bg-red-900/10 text-center">
      <p class="text-sm font-semibold text-red-700 dark:text-red-400">Could not load the dashboard</p>
      <p class="text-sm text-red-600/80 dark:text-red-400/70 mt-1">{{ loadError }}</p>
      <button @click="refresh" class="btn-primary mt-4 !px-5 !py-2 text-sm">Try again</button>
    </div>

    <LoadingSpinner v-else-if="submissionStore.loading && !submissionStore.orgStats" />

    <!-- Onboarding empty state -->
    <div v-else-if="isEmpty" class="card p-10 text-center">
      <div class="text-4xl mb-3">📭</div>
      <h2 class="text-lg font-bold text-secondary dark:text-white">No submissions yet</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-md mx-auto">
        Share your organization's submission link or QR code so citizens can start
        sending complaints, feedback, and suggestions.
      </p>
      <div class="flex items-center justify-center gap-3 mt-5 flex-wrap">
        <RouterLink to="/org/qrcode" class="btn-primary !px-5 !py-2.5 text-sm">Get QR code</RouterLink>
        <RouterLink
          :to="orgStore.currentOrg?.slug ? `/submit/${orgStore.currentOrg.slug}` : '/submit'"
          class="btn-secondary !px-5 !py-2.5 text-sm">
          View submission form
        </RouterLink>
      </div>
    </div>

    <template v-else>
      <!-- Stat cards — each links to the matching filtered view -->
      <div class="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <RouterLink to="/org/submissions" class="block rounded-2xl hover:shadow-md transition-shadow">
          <StatsCard label="Total Submissions" :value="s.total ?? 0" icon="📋" />
        </RouterLink>
        <RouterLink to="/org/submissions?status=submitted,acknowledged" class="block rounded-2xl hover:shadow-md transition-shadow">
          <StatsCard label="Pending" :value="s.pending ?? 0" icon="⏳" color="orange" sub="Awaiting review" />
        </RouterLink>
        <RouterLink to="/org/submissions?status=in_review" class="block rounded-2xl hover:shadow-md transition-shadow">
          <StatsCard label="In Review" :value="s.in_review ?? 0" icon="🔍" color="blue" />
        </RouterLink>
        <RouterLink to="/org/submissions?status=escalated" class="block rounded-2xl hover:shadow-md transition-shadow">
          <StatsCard label="Escalated" :value="s.escalated ?? 0" icon="🔺" color="orange" />
        </RouterLink>
        <RouterLink to="/org/submissions?status=resolved" class="block rounded-2xl hover:shadow-md transition-shadow">
          <StatsCard
            label="Resolved This Month"
            :value="s.resolved_this_month ?? 0"
            icon="✅"
            color="green"
            :sub="s.avg_resolution_days ? `Avg ${s.avg_resolution_days} days to resolve` : ''" />
        </RouterLink>
        <RouterLink to="/org/submissions?assignee=unassigned" class="block rounded-2xl hover:shadow-md transition-shadow">
          <StatsCard label="Unassigned" :value="s.unassigned_count ?? 0" icon="👤" sub="Active, no owner" />
        </RouterLink>
        <RouterLink to="/org/submissions?status=resolved,closed" class="block rounded-2xl hover:shadow-md transition-shadow">
          <StatsCard
            label="Resolution Rate"
            :value="resolutionRate === null ? '—' : `${resolutionRate}%`"
            icon="📈"
            color="green"
            sub="Resolved or closed" />
        </RouterLink>
        <RouterLink to="/org/staff" class="block rounded-2xl hover:shadow-md transition-shadow">
          <StatsCard label="Staff Members" :value="s.staff_count ?? 0" icon="🧑‍💼" sub="Manage your team" />
        </RouterLink>
      </div>

      <!-- Charts row -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div class="card p-5 lg:col-span-2">
          <h2 class="text-sm font-bold text-gray-800 dark:text-white mb-4">Submission Trend — Last 7 Days</h2>
          <TrendChart :data="trendData" />
        </div>
        <div class="card p-5">
          <h2 class="text-sm font-bold text-gray-800 dark:text-white mb-4">By Status</h2>
          <StatusDonut :data="statusBreakdown" />
        </div>
      </div>

      <!-- Needs attention + breakdowns -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div class="card p-5 lg:col-span-2">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-sm font-bold text-gray-800 dark:text-white">Needs Attention</h2>
            <RouterLink to="/org/submissions?status=submitted,acknowledged,in_review,escalated"
              class="text-xs text-primary hover:underline font-medium">
              View all active →
            </RouterLink>
          </div>

          <div v-if="!needsAttention.length" class="text-sm text-gray-400 dark:text-gray-500 text-center py-6">
            All caught up — no active submissions. 🎉
          </div>
          <div v-else class="divide-y divide-gray-100 dark:divide-gray-700/50 -my-2">
            <RouterLink
              v-for="sub in needsAttention"
              :key="sub.id"
              :to="{ path: '/org/submissions', query: { ref: sub.reference_number } }"
              class="flex items-center gap-3 py-2.5 group">
              <PriorityBadge :priority="sub.priority" />
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-900 dark:text-white truncate group-hover:text-primary transition-colors">
                  {{ sub.title }}
                </p>
                <p class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                  <span class="font-mono">{{ sub.reference_number }}</span>
                  · waiting {{ ageDays(sub.created_at) }}
                  <span v-if="!sub.assigned_to"> · unassigned</span>
                </p>
              </div>
              <StatusBadge :status="sub.status" />
            </RouterLink>
          </div>
        </div>

        <div class="space-y-5">
          <div class="card p-5">
            <h2 class="text-sm font-bold text-gray-800 dark:text-white mb-4">By Type</h2>
            <div class="space-y-3">
              <div v-for="row in typeRows" :key="row.key">
                <div class="flex items-center justify-between text-xs mb-1">
                  <span class="text-gray-600 dark:text-gray-300 font-medium">{{ row.icon }} {{ row.label }}</span>
                  <span class="text-gray-400 dark:text-gray-500 font-semibold">{{ row.count }}</span>
                </div>
                <div class="h-2 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                  <div :class="['h-full rounded-full transition-all', row.bar]" :style="{ width: row.width }" />
                </div>
              </div>
            </div>
          </div>

          <div class="card p-5">
            <h2 class="text-sm font-bold text-gray-800 dark:text-white mb-4">By Priority</h2>
            <div class="space-y-3">
              <div v-for="row in priorityRows" :key="row.key">
                <div class="flex items-center justify-between text-xs mb-1">
                  <span class="text-gray-600 dark:text-gray-300 font-medium">{{ row.label }}</span>
                  <span class="text-gray-400 dark:text-gray-500 font-semibold">{{ row.count }}</span>
                </div>
                <div class="h-2 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                  <div :class="['h-full rounded-full transition-all', row.bar]" :style="{ width: row.width }" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Recent activity -->
      <div class="card p-5">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-sm font-bold text-gray-800 dark:text-white">Recent Activity</h2>
          <RouterLink to="/org/submissions" class="text-xs text-primary hover:underline font-medium">
            View all →
          </RouterLink>
        </div>
        <ActivityFeed :activities="recentActivity" />
      </div>

      <!-- Quick-action links -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <RouterLink to="/org/submissions"
          class="card p-4 text-center hover:shadow-md transition-shadow group">
          <div class="w-10 h-10 rounded-xl bg-primary/10 dark:bg-primary/20 flex items-center justify-center mx-auto mb-2 group-hover:bg-primary/20 transition-colors">
            <svg class="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
          </div>
          <p class="text-sm font-semibold text-gray-800 dark:text-white">All Submissions</p>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">View &amp; manage</p>
        </RouterLink>

        <RouterLink to="/org/staff"
          class="card p-4 text-center hover:shadow-md transition-shadow group">
          <div class="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center mx-auto mb-2 group-hover:bg-blue-100 transition-colors">
            <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
          </div>
          <p class="text-sm font-semibold text-gray-800 dark:text-white">Staff</p>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Manage team</p>
        </RouterLink>

        <RouterLink to="/org/qrcode"
          class="card p-4 text-center hover:shadow-md transition-shadow group">
          <div class="w-10 h-10 rounded-xl bg-green-50 dark:bg-green-900/20 flex items-center justify-center mx-auto mb-2 group-hover:bg-green-100 transition-colors">
            <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z"/>
            </svg>
          </div>
          <p class="text-sm font-semibold text-gray-800 dark:text-white">QR Code</p>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Download &amp; share</p>
        </RouterLink>

        <RouterLink
          :to="orgStore.currentOrg?.slug ? `/organizations/${orgStore.currentOrg.slug}` : '/organizations'"
          class="card p-4 text-center hover:shadow-md transition-shadow group">
          <div class="w-10 h-10 rounded-xl bg-gray-50 dark:bg-gray-700 flex items-center justify-center mx-auto mb-2 group-hover:bg-gray-100 dark:group-hover:bg-gray-600 transition-colors">
            <svg class="w-5 h-5 text-gray-600 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
            </svg>
          </div>
          <p class="text-sm font-semibold text-gray-800 dark:text-white">Public View</p>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">See your profile</p>
        </RouterLink>
      </div>
    </template>
  </div>
</template>
