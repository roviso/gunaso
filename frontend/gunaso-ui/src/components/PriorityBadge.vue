<script setup>
import { computed } from 'vue'

const props = defineProps({ priority: { type: String, required: true } })

const config = computed(() => {
  const map = {
    low:    { label: 'Low',    cls: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300' },
    medium: { label: 'Medium', cls: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300' },
    high:   { label: 'High',   cls: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' },
    urgent: { label: 'Urgent', cls: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 font-bold' },
  }
  return map[props.priority] || map.low
})
</script>

<template>
  <span :class="['inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-semibold', config.cls]">
    {{ config.label }}
  </span>
</template>
