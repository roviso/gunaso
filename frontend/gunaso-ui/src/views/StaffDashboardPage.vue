<script setup>
import { computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useSubmissionStore } from '@/stores/submission'
import StatsCard from '@/components/StatsCard.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import PriorityBadge from '@/components/PriorityBadge.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const authStore = useAuthStore()
const submissionStore = useSubmissionStore()

// Every widget below is gated on the specific privilege it needs — a role
// with zero matching privileges sees the "ask your admin" empty state rather
// than a dashboard that looks broken.
const canViewStats = computed(() => authStore.hasPrivilege('view_stats'))
const canViewSubmissions = computed(() => authStore.hasPrivilege('view_submissions'))
const canViewStaff = computed(() => authStore.hasPrivilege('view_staff'))
const canManageRoles = computed(() => authStore.hasPrivilege('manage_roles'))

const hasAnyPrivilege = computed(() => (authStore.staffAccess.privileges || []).length > 0)

const stats = computed(() => submissionStore.orgStats || {})
const myQueue = computed(() => submissionStore.orgSubmissions)

onMounted(async () => {
  if (canViewStats.value) submissionStore.fetchOrgStats()
  if (canViewSubmissions.value) submissionStore.fetchOrgSubmissions({ assigned_to: 'me', page_size: 10 })
})
</script>

<template>
  <div class="p-6 space-y-6">
    <!-- Role banner -->
    <div class="card p-5 flex items-center justify-between flex-wrap gap-3">
      <div>
        <p class="text-sm text-gray-500 dark:text-gray-400">Signed in at</p>
        <h1 class="text-xl font-extrabold text-secondary dark:text-white">{{ authStore.staffAccess.organization_name }}</h1>
      </div>
      <span class="px-3 py-1.5 rounded-full text-sm font-semibold bg-secondary/10 text-secondary dark:bg-white/10 dark:text-white">
        {{ authStore.staffAccess.role_name || 'Staff' }}
      </span>
    </div>

    <!-- No privileges at all -->
    <div v-if="!hasAnyPrivilege" class="card p-12 text-center">
      <div class="w-14 h-14 rounded-2xl bg-gray-100 dark:bg-gray-700 flex items-center justify-center mx-auto mb-4">
        <svg class="w-7 h-7 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
        </svg>
      </div>
      <p class="font-semibold text-gray-700 dark:text-gray-200">Your role doesn't grant any dashboard access yet</p>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Ask your organization admin to add privileges to your role.</p>
    </div>

    <template v-else>
      <!-- Stats -->
      <div v-if="canViewStats" class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard label="Total" :value="stats.total ?? '—'" icon="📥" />
        <StatsCard label="Pending" :value="stats.pending ?? '—'" color="orange" icon="⏳" />
        <StatsCard label="In Review" :value="stats.in_review ?? '—'" color="blue" icon="🔍" />
        <StatsCard label="Resolved This Month" :value="stats.resolved_this_month ?? '—'" color="green" icon="✅" />
      </div>

      <!-- Assigned to me -->
      <div v-if="canViewSubmissions" class="card p-5">
        <div class="flex items-center justify-between mb-4">
          <h2 class="font-bold text-secondary dark:text-white">Assigned to me</h2>
          <RouterLink to="/org/submissions" class="text-xs font-semibold text-primary hover:text-primary-600">View all submissions →</RouterLink>
        </div>

        <LoadingSpinner v-if="submissionStore.loading" />

        <p v-else-if="!myQueue.length" class="text-sm text-gray-500 dark:text-gray-400 py-6 text-center">
          Nothing assigned to you right now.
        </p>

        <div v-else class="space-y-2">
          <RouterLink v-for="sub in myQueue" :key="sub.reference_number"
            :to="`/org/submissions?ref=${sub.reference_number}`"
            class="flex items-center gap-3 p-3 rounded-xl border border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
            <div class="flex-1 min-w-0">
              <p class="text-sm font-semibold text-gray-900 dark:text-white truncate">{{ sub.title }}</p>
              <p class="text-xs text-gray-400 dark:text-gray-500">{{ sub.reference_number }}</p>
            </div>
            <PriorityBadge :priority="sub.priority" />
            <StatusBadge :status="sub.status" />
          </RouterLink>
        </div>
      </div>

      <!-- Quick links -->
      <div class="grid sm:grid-cols-2 gap-4">
        <RouterLink v-if="canViewSubmissions" to="/org/submissions" class="card p-5 hover:-translate-y-0.5 transition-transform">
          <p class="font-semibold text-gray-900 dark:text-white">Submissions</p>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Browse and act on the organization's queue.</p>
        </RouterLink>
        <RouterLink v-if="canViewStaff" to="/org/staff" class="card p-5 hover:-translate-y-0.5 transition-transform">
          <p class="font-semibold text-gray-900 dark:text-white">Staff</p>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">See who else is on the team.</p>
        </RouterLink>
        <RouterLink v-if="canManageRoles" to="/org/roles" class="card p-5 hover:-translate-y-0.5 transition-transform">
          <p class="font-semibold text-gray-900 dark:text-white">Roles</p>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Manage custom roles and privileges.</p>
        </RouterLink>
      </div>
    </template>
  </div>
</template>
