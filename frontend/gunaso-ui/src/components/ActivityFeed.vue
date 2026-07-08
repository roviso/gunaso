<script setup>
defineProps({
  activities: { type: Array, default: () => [] }
})

const STATUS_DOT = {
  submitted:    'bg-amber-500',
  acknowledged: 'bg-cyan-500',
  in_review:    'bg-blue-500',
  resolved:     'bg-green-500',
  escalated:    'bg-orange-500',
  rejected:     'bg-red-500',
  closed:       'bg-gray-400',
}

const STATUS_LABEL = {
  submitted: 'Submitted', acknowledged: 'Acknowledged', in_review: 'In Review',
  resolved: 'Resolved', escalated: 'Escalated', rejected: 'Rejected', closed: 'Closed',
}

function formatRelative(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
</script>

<template>
  <div v-if="!activities.length" class="text-sm text-gray-400 dark:text-gray-500 text-center py-6">
    No recent activity to display.
  </div>
  <div v-else class="space-y-3">
    <div v-for="(act, i) in activities" :key="i" class="flex items-start gap-3">
      <div :class="['w-2 h-2 rounded-full mt-2 shrink-0', STATUS_DOT[act.new_status] || 'bg-gray-400']" />
      <div class="flex-1 min-w-0">
        <p class="text-sm text-gray-800 dark:text-gray-200 leading-snug">
          <span class="font-semibold">{{ act.updated_by_name || 'Staff' }}</span>
          moved
          <span class="font-mono text-xs bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded text-gray-600 dark:text-gray-300">
            {{ act.reference || act.submission_reference }}
          </span>
          to
          <span class="font-semibold capitalize">{{ STATUS_LABEL[act.new_status] || act.new_status }}</span>
        </p>
        <p v-if="act.note" class="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate italic">
          "{{ act.note }}"
        </p>
      </div>
      <span class="text-xs text-gray-400 dark:text-gray-500 shrink-0 mt-0.5">
        {{ formatRelative(act.created_at) }}
      </span>
    </div>
  </div>
</template>
