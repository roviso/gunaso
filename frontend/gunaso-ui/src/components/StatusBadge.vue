<script setup>
import { computed } from 'vue'

const props = defineProps({ status: { type: String, required: true } })

const config = computed(() => {
  const map = {
    submitted:    { label: 'Submitted',    cls: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300', dot: 'bg-amber-500' },
    acknowledged: { label: 'Acknowledged', cls: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-300',   dot: 'bg-cyan-500'  },
    in_review:    { label: 'In Review',    cls: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',   dot: 'bg-blue-500'  },
    resolved:     { label: 'Resolved',     cls: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300', dot: 'bg-green-500' },
    escalated:    { label: 'Escalated',    cls: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300', dot: 'bg-orange-500' },
    closed:       { label: 'Closed',       cls: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',        dot: 'bg-gray-400'  },
    rejected:     { label: 'Rejected',     cls: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',         dot: 'bg-red-500'   },
  }
  return map[props.status] || map.submitted
})
</script>

<template>
  <span :class="['inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold', config.cls]">
    <span :class="['w-1.5 h-1.5 rounded-full', config.dot]"></span>
    {{ config.label }}
  </span>
</template>
