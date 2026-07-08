<script setup>
defineProps({
  member: { type: Object, required: true },
  canEdit: { type: Boolean, default: true },
})
defineEmits(['change-role', 'remove'])

const ROLE_STYLE = {
  manager:    'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  supervisor: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  agent:      'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  viewer:     'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
}

function initial(m) {
  const name = m.name || m.user?.name || m.email || '?'
  return name[0].toUpperCase()
}

function displayName(m) {
  return m.name || m.user?.name || m.email || 'Unknown'
}

function displayEmail(m) {
  return m.email || m.user?.email || ''
}
</script>

<template>
  <div class="card p-4 flex items-center gap-4">
    <!-- Avatar -->
    <div class="w-10 h-10 rounded-full bg-secondary text-white flex items-center justify-center text-sm font-bold shrink-0">
      {{ initial(member) }}
    </div>

    <!-- Info -->
    <div class="flex-1 min-w-0">
      <div class="flex items-center flex-wrap gap-2 mb-0.5">
        <p class="font-semibold text-gray-900 dark:text-white text-sm">{{ displayName(member) }}</p>
        <span :class="['px-2 py-0.5 rounded-full text-xs font-semibold capitalize', ROLE_STYLE[member.role] || ROLE_STYLE.agent]">
          {{ member.role || 'agent' }}
        </span>
        <span v-if="member.is_active === false"
          class="px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-600 dark:bg-red-900/20 dark:text-red-400">
          Inactive
        </span>
      </div>
      <p class="text-xs text-gray-500 dark:text-gray-400">{{ displayEmail(member) }}</p>
      <p v-if="member.active_submissions_count !== undefined" class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
        {{ member.active_submissions_count }} active submissions
      </p>
    </div>

    <!-- Actions -->
    <div v-if="canEdit" class="flex items-center gap-1 shrink-0">
      <button @click="$emit('change-role', member)"
        class="p-1.5 rounded-lg text-gray-400 hover:text-secondary dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        title="Edit role">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
        </svg>
      </button>
      <button @click="$emit('remove', member)"
        class="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/10 transition-colors"
        title="Remove">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
        </svg>
      </button>
    </div>
  </div>
</template>
