<script setup>
import { computed } from 'vue'

const props = defineProps({
  timeline: { type: Array, default: () => [] }
})

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

const statusConfig = {
  submitted:    { label: 'Submitted',    color: 'bg-gray-400',   ring: 'ring-gray-200 dark:ring-gray-700' },
  acknowledged: { label: 'Acknowledged', color: 'bg-cyan-500',   ring: 'ring-cyan-100 dark:ring-cyan-900/30' },
  in_review:    { label: 'In Review',    color: 'bg-blue-500',   ring: 'ring-blue-100 dark:ring-blue-900/30' },
  resolved:     { label: 'Resolved',     color: 'bg-green-500',  ring: 'ring-green-100 dark:ring-green-900/30' },
  escalated:    { label: 'Escalated',    color: 'bg-orange-500', ring: 'ring-orange-100 dark:ring-orange-900/30' },
  closed:       { label: 'Closed',       color: 'bg-gray-500',   ring: 'ring-gray-200 dark:ring-gray-700' },
  rejected:     { label: 'Rejected',     color: 'bg-red-500',    ring: 'ring-red-100 dark:ring-red-900/30' },
}

function getConfig(status) {
  return statusConfig[status] || statusConfig.submitted
}
</script>

<template>
  <div class="flow-root">
    <ul class="-mb-8">
      <li v-for="(item, idx) in timeline" :key="idx" class="relative pb-8">
        <span v-if="idx < timeline.length - 1"
          class="absolute left-4 top-8 -ml-px h-full w-0.5 bg-gray-200 dark:bg-gray-700" />
        <div class="relative flex items-start gap-3">
          <div :class="['h-8 w-8 rounded-full ring-4 flex items-center justify-center shrink-0', getConfig(item.status).color, getConfig(item.status).ring]">
            <svg v-if="item.status === 'resolved'" class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
            </svg>
            <svg v-else-if="item.status === 'rejected'" class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12"/>
            </svg>
            <span v-else class="w-2 h-2 bg-white rounded-full" />
          </div>
          <div class="min-w-0 flex-1 pt-1">
            <div class="flex items-center justify-between gap-2 flex-wrap">
              <p class="text-sm font-semibold text-gray-900 dark:text-white capitalize">
                {{ getConfig(item.status).label }}
              </p>
              <time class="text-xs text-gray-400 dark:text-gray-500 shrink-0">{{ formatDate(item.created_at) }}</time>
            </div>
            <p v-if="item.note" class="mt-1 text-sm text-gray-600 dark:text-gray-400">{{ item.note }}</p>
            <p v-if="item.updated_by" class="mt-0.5 text-xs text-gray-400 dark:text-gray-500">by {{ item.updated_by }}</p>
          </div>
        </div>
      </li>
    </ul>
  </div>
</template>
