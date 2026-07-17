<script setup>
import { onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const adminStore = useAdminStore()

const ACTION_META = {
  organization_verified: { label: 'Verified organization', cls: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' },
  organization_unverified: { label: 'Unverified organization', cls: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300' },
  organization_activated: { label: 'Activated organization', cls: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' },
  organization_deactivated: { label: 'Deactivated organization', cls: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' },
  user_blocked: { label: 'Blocked user', cls: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' },
  user_unblocked: { label: 'Unblocked user', cls: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' },
  user_promoted: { label: 'Promoted to superadmin', cls: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300' },
  user_demoted: { label: 'Demoted from superadmin', cls: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400' },
}

function actionMeta(action) {
  return ACTION_META[action] || { label: action, cls: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400' }
}

function formatTimestamp(iso) {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit',
  })
}

onMounted(() => adminStore.fetchAuditLog())
</script>

<template>
  <div class="p-6 space-y-5">
    <div>
      <h1 class="text-xl font-extrabold text-secondary dark:text-white">Audit Log</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
        Every superadmin action, append-only — who did what, and when.
      </p>
    </div>

    <LoadingSpinner v-if="adminStore.auditLogLoading" />

    <div v-else-if="adminStore.auditLogError" class="card p-6 text-center">
      <p class="text-sm text-red-500 dark:text-red-400">{{ adminStore.auditLogError }}</p>
    </div>

    <div v-else-if="!adminStore.auditLog.length" class="card p-12 text-center">
      <p class="font-semibold text-gray-700 dark:text-gray-200">No superadmin actions recorded yet</p>
    </div>

    <div v-else class="card divide-y divide-gray-100 dark:divide-gray-700/50">
      <div v-for="entry in adminStore.auditLog" :key="entry.id" class="flex items-start gap-4 p-4">
        <span :class="['shrink-0 inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold', actionMeta(entry.action).cls]">
          {{ actionMeta(entry.action).label }}
        </span>
        <div class="flex-1 min-w-0">
          <p class="text-sm text-gray-800 dark:text-gray-200">
            <span class="font-semibold">{{ entry.actor_name }}</span>
            acted on
            <span class="font-semibold">{{ entry.target_repr }}</span>
            <span class="text-gray-400 dark:text-gray-500">({{ entry.target_type }})</span>
          </p>
          <p v-if="entry.note" class="text-xs text-gray-500 dark:text-gray-400 mt-1">{{ entry.note }}</p>
        </div>
        <span class="shrink-0 text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap">
          {{ formatTimestamp(entry.created_at) }}
        </span>
      </div>
    </div>
  </div>
</template>
