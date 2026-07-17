<script setup>
import { computed, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'
import StatsCard from '@/components/StatsCard.vue'
import TrendChart from '@/components/TrendChart.vue'
import StatusDonut from '@/components/StatusDonut.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const adminStore = useAdminStore()

const o = computed(() => adminStore.overview || {})

function formatDayLabel(isoDate) {
  return new Date(isoDate + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const submissionTrend = computed(() =>
  (o.value.trend || []).map((d) => ({ label: formatDayLabel(d.date), count: d.submissions }))
)
const userTrend = computed(() =>
  (o.value.trend || []).map((d) => ({ label: formatDayLabel(d.date), count: d.users }))
)

async function refresh() {
  await adminStore.fetchOverview()
}

onMounted(refresh)
</script>

<template>
  <div class="p-6 space-y-6">
    <div class="flex items-start justify-between gap-4 flex-wrap">
      <div>
        <h1 class="text-xl font-extrabold text-secondary dark:text-white">Platform Overview</h1>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
          Cross-organization analytics — how Gunaso is performing as a whole.
        </p>
      </div>
      <button
        @click="refresh"
        :disabled="adminStore.overviewLoading"
        class="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium text-gray-600 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50">
        <svg :class="['w-4 h-4', adminStore.overviewLoading && 'animate-spin']" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
        </svg>
        Refresh
      </button>
    </div>

    <div v-if="adminStore.overviewError && !adminStore.overview"
      class="card p-6 border-red-200 dark:border-red-900/50 bg-red-50/50 dark:bg-red-900/10 text-center">
      <p class="text-sm font-semibold text-red-700 dark:text-red-400">Could not load the platform overview</p>
      <p class="text-sm text-red-600/80 dark:text-red-400/70 mt-1">{{ adminStore.overviewError }}</p>
      <button @click="refresh" class="btn-primary mt-4 !px-5 !py-2 text-sm">Try again</button>
    </div>

    <LoadingSpinner v-else-if="adminStore.overviewLoading && !adminStore.overview" />

    <template v-else-if="adminStore.overview">
      <!-- Stat cards -->
      <div class="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <RouterLink to="/admin/organizations" class="block rounded-2xl hover:shadow-md transition-shadow">
          <StatsCard label="Organizations" :value="o.organizations.total" icon="🏢" />
        </RouterLink>
        <RouterLink to="/admin/organizations" class="block rounded-2xl hover:shadow-md transition-shadow">
          <StatsCard label="Pending Verification" :value="o.organizations.unverified" icon="⏳" color="orange" sub="Awaiting your review" />
        </RouterLink>
        <RouterLink to="/admin/users" class="block rounded-2xl hover:shadow-md transition-shadow">
          <StatsCard label="Users" :value="o.users.total" icon="👥" color="blue" :sub="`${o.users.blocked} blocked`" />
        </RouterLink>
        <RouterLink to="/admin/users" class="block rounded-2xl hover:shadow-md transition-shadow">
          <StatsCard label="Superadmins" :value="o.users.superadmins" icon="🛡️" />
        </RouterLink>
        <RouterLink to="/admin/submissions" class="block rounded-2xl hover:shadow-md transition-shadow">
          <StatsCard label="Total Submissions" :value="o.submissions.total" icon="📋" />
        </RouterLink>
        <div class="block rounded-2xl">
          <StatsCard label="Avg Resolution" :value="`${o.submissions.avg_resolution_days}d`" icon="📈" color="green" />
        </div>
        <div class="block rounded-2xl">
          <StatsCard label="Active Organizations" :value="o.organizations.active" icon="✅" color="green" />
        </div>
        <div class="block rounded-2xl">
          <StatsCard label="Deactivated Organizations" :value="o.organizations.inactive" icon="🚫" />
        </div>
      </div>

      <!-- Charts row -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div class="card p-5 lg:col-span-2 space-y-6">
          <div>
            <h2 class="text-sm font-bold text-gray-800 dark:text-white mb-4">Submissions — Last 30 Days</h2>
            <TrendChart :data="submissionTrend" label="Submissions" />
          </div>
          <div>
            <h2 class="text-sm font-bold text-gray-800 dark:text-white mb-4">New Signups — Last 30 Days</h2>
            <TrendChart :data="userTrend" label="New Users" />
          </div>
        </div>
        <div class="card p-5">
          <h2 class="text-sm font-bold text-gray-800 dark:text-white mb-4">Submissions by Status</h2>
          <StatusDonut :data="o.submissions.by_status" />
        </div>
      </div>

      <!-- User type breakdown -->
      <div class="card p-5">
        <h2 class="text-sm font-bold text-gray-800 dark:text-white mb-4">Users by Type</h2>
        <div class="grid grid-cols-3 gap-4 text-center">
          <div v-for="(count, type) in o.users.by_type" :key="type" class="p-3 rounded-xl bg-gray-50 dark:bg-gray-900">
            <p class="text-2xl font-extrabold text-secondary dark:text-white">{{ count }}</p>
            <p class="text-xs text-gray-500 dark:text-gray-400 capitalize mt-1">{{ type.replace('_', ' ') }}</p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
