<script setup>
import StatusBadge from './StatusBadge.vue'
import PriorityBadge from './PriorityBadge.vue'

defineProps({
  submission: { type: Object, required: true }
})

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

const typeIcon = { complaint: '⚠️', feedback: '💬', suggestion: '💡' }
</script>

<template>
  <div class="card p-4 hover:shadow-md transition-shadow duration-200 cursor-pointer group">
    <div class="flex items-start justify-between gap-3 mb-3">
      <div class="flex items-start gap-2 min-w-0">
        <span class="text-base leading-none mt-0.5">{{ typeIcon[submission.type] || '📋' }}</span>
        <div class="min-w-0">
          <p class="font-semibold text-gray-900 dark:text-white text-sm line-clamp-2 group-hover:text-primary transition-colors">
            {{ submission.title }}
          </p>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{{ submission.organization_name }}</p>
        </div>
      </div>
      <StatusBadge :status="submission.status" />
    </div>

    <div class="flex items-center gap-2 flex-wrap">
      <span class="text-xs font-mono text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-700/50 px-2 py-0.5 rounded">
        {{ submission.reference_number }}
      </span>
      <PriorityBadge :priority="submission.priority" />
      <span class="text-xs text-gray-400 dark:text-gray-500 ml-auto">{{ formatDate(submission.created_at) }}</span>
    </div>
  </div>
</template>
