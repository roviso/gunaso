<script setup>
import { computed, onMounted } from 'vue'
import { useSubmissionStore } from '@/stores/submission'
import { useOrganizationStore } from '@/stores/organization'
import { useAuthStore } from '@/stores/auth'
import StatsCard from '@/components/StatsCard.vue'
import TrendChart from '@/components/TrendChart.vue'
import StatusDonut from '@/components/StatusDonut.vue'
import ActivityFeed from '@/components/ActivityFeed.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const submissionStore = useSubmissionStore()
const orgStore = useOrganizationStore()
const authStore = useAuthStore()

// 7-day trend derived from loaded submissions (fallback when backend doesn't return trend data)
const trendData = computed(() => {
  const s = submissionStore.orgStats
  if (s?.trend && Array.isArray(s.trend)) return s.trend
  const now = new Date()
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(now)
    d.setDate(d.getDate() - (6 - i))
    const dateStr = d.toISOString().slice(0, 10)
    const label = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    const count = submissionStore.orgSubmissions.filter((sub) =>
      sub.created_at?.startsWith(dateStr)
    ).length
    return { label, count }
  })
})

// Status breakdown: prefer API data, fall back to counting from loaded submissions
const statusBreakdown = computed(() => {
  const s = submissionStore.orgStats
  if (s?.by_status && typeof s.by_status === 'object') return s.by_status
  const result = {}
  for (const sub of submissionStore.orgSubmissions) {
    result[sub.status] = (result[sub.status] || 0) + 1
  }
  return result
})

// Recent activity: flatten all submission timelines and sort by date
const recentActivity = computed(() => {
  return submissionStore.orgSubmissions
    .flatMap((sub) =>
      (sub.timeline || []).map((t) => ({
        ...t,
        reference: sub.reference_number,
      }))
    )
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .slice(0, 8)
})

// Convenience alias for stats object
const s = computed(() => submissionStore.orgStats || {})

// Unassigned count
const unassignedCount = computed(() =>
  s.value.unassigned ??
  submissionStore.orgSubmissions.filter((x) => !x.assigned_to).length
)

onMounted(async () => {
  await Promise.all([
    submissionStore.fetchOrgSubmissions({ page_size: 100 }),
    submissionStore.fetchOrgStats(),
  ])
})
</script>

<template>
  <div class="p-6 space-y-6">
    <!-- Page header -->
    <div>
      <h1 class="text-xl font-extrabold text-secondary dark:text-white">Dashboard</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
        Overview for
        <span class="font-semibold text-gray-700 dark:text-gray-200">
          {{ orgStore.currentOrg?.name || authStore.user?.organization_name || 'your organization' }}
        </span>
      </p>
    </div>

    <LoadingSpinner v-if="submissionStore.loading && !submissionStore.orgStats" />

    <template v-else>
      <!-- Stats cards -->
      <div class="grid grid-cols-2 xl:grid-cols-3 gap-4">
        <StatsCard
          label="Total Submissions"
          :value="s.total ?? submissionStore.orgSubmissions.length"
          icon="📋" />
        <StatsCard
          label="Submitted / Pending"
          :value="(s.submitted ?? 0) + (s.pending ?? 0)"
          icon="⏳"
          color="orange"
          sub="Needs attention" />
        <StatsCard
          label="In Review"
          :value="s.in_review ?? statusBreakdown.in_review ?? 0"
          icon="🔍"
          color="blue" />
        <StatsCard
          label="Resolved This Month"
          :value="s.resolved_month ?? s.resolved ?? statusBreakdown.resolved ?? 0"
          icon="✅"
          color="green"
          :sub="s.avg_resolution_days ? `Avg ${s.avg_resolution_days} days` : ''" />
        <StatsCard
          label="Escalated"
          :value="s.escalated ?? statusBreakdown.escalated ?? 0"
          icon="🔺"
          color="orange" />
        <StatsCard
          label="Unassigned"
          :value="unassignedCount"
          icon="👤" />
      </div>

      <!-- Charts row -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <!-- Trend line chart -->
        <div class="card p-5 lg:col-span-2">
          <h2 class="text-sm font-bold text-gray-800 dark:text-white mb-4">Submission Trend — Last 7 Days</h2>
          <TrendChart :data="trendData" />
        </div>

        <!-- Status donut -->
        <div class="card p-5">
          <h2 class="text-sm font-bold text-gray-800 dark:text-white mb-4">By Status</h2>
          <StatusDonut :data="statusBreakdown" />
        </div>
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
    </template>
  </div>
</template>
