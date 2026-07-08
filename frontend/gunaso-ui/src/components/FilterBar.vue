<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Object, required: true },
  statuses: { type: Array, default: () => [] },
  showDateRange: { type: Boolean, default: false },
  showAssignee: { type: Boolean, default: false },
  staffList: { type: Array, default: () => [] },
  count: { type: Number, default: 0 },
})

const emit = defineEmits(['update:modelValue', 'clear'])

const hasFilters = computed(() => {
  const f = props.modelValue
  return !!(f.status || f.type || f.priority || f.search || f.assignee || f.dateFrom || f.dateTo)
})

function update(field, value) {
  emit('update:modelValue', { ...props.modelValue, [field]: value })
}
</script>

<template>
  <div class="card p-4">
    <div class="flex flex-wrap gap-3 items-center">
      <!-- Search -->
      <div class="relative min-w-[200px] flex-1 max-w-xs">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"
          fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0"/>
        </svg>
        <input
          :value="modelValue.search"
          @input="update('search', $event.target.value)"
          type="text"
          placeholder="Search reference, title..."
          class="input-base pl-9" />
      </div>

      <!-- Status -->
      <select v-if="statuses.length"
        :value="modelValue.status"
        @change="update('status', $event.target.value)"
        class="input-base w-auto min-w-[140px]">
        <option value="">All Statuses</option>
        <option v-for="s in statuses" :key="s.value" :value="s.value">{{ s.label }}</option>
      </select>

      <!-- Type -->
      <select
        :value="modelValue.type"
        @change="update('type', $event.target.value)"
        class="input-base w-auto min-w-[120px]">
        <option value="">All Types</option>
        <option value="complaint">Complaint</option>
        <option value="feedback">Feedback</option>
        <option value="suggestion">Suggestion</option>
      </select>

      <!-- Priority -->
      <select
        :value="modelValue.priority"
        @change="update('priority', $event.target.value)"
        class="input-base w-auto min-w-[130px]">
        <option value="">All Priorities</option>
        <option value="urgent">Urgent</option>
        <option value="high">High</option>
        <option value="medium">Medium</option>
        <option value="low">Low</option>
      </select>

      <!-- Assignee -->
      <template v-if="showAssignee">
        <select
          :value="modelValue.assignee"
          @change="update('assignee', $event.target.value)"
          class="input-base w-auto min-w-[130px]">
          <option value="">All Assignees</option>
          <option value="unassigned">Unassigned</option>
          <option v-for="s in staffList" :key="s.id" :value="String(s.id)">
            {{ s.name || s.user?.name || s.email }}
          </option>
        </select>
      </template>

      <!-- Date range -->
      <template v-if="showDateRange">
        <input
          type="date"
          :value="modelValue.dateFrom"
          @change="update('dateFrom', $event.target.value)"
          class="input-base w-auto"
          title="From" />
        <input
          type="date"
          :value="modelValue.dateTo"
          @change="update('dateTo', $event.target.value)"
          class="input-base w-auto"
          title="To" />
      </template>

      <!-- Clear -->
      <button v-if="hasFilters" @click="$emit('clear')"
        class="inline-flex items-center gap-1.5 px-3 py-2.5 rounded-xl text-sm font-medium text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/10 transition-colors">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12"/>
        </svg>
        Clear
      </button>

      <span class="ml-auto text-sm text-gray-500 dark:text-gray-400 shrink-0">
        <span class="font-semibold text-gray-900 dark:text-white">{{ count }}</span> results
      </span>
    </div>
  </div>
</template>
