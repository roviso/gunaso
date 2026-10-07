<script setup>
// The append-only case history, rendered as a conversation: status changes
// as milestones, organization replies and citizen follow-ups as messages,
// and internal notes (organization side only — the API strips them for
// everyone else) visibly marked as such.
const props = defineProps({
  timeline: { type: Array, default: () => [] },
  // 'citizen' labels follow-ups as "You"; 'org' labels them "Citizen".
  audience: { type: String, default: 'citizen' },
  organizationName: { type: String, default: '' },
})

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

const statusConfig = {
  submitted:    { label: 'Submitted',    color: 'bg-gray-400' },
  acknowledged: { label: 'Acknowledged', color: 'bg-cyan-500' },
  in_review:    { label: 'In review',    color: 'bg-blue-500' },
  resolved:     { label: 'Resolved',     color: 'bg-green-500' },
  escalated:    { label: 'Escalated',    color: 'bg-orange-500' },
  closed:       { label: 'Closed',       color: 'bg-gray-500' },
  rejected:     { label: 'Rejected',     color: 'bg-red-500' },
}

function kindOf(item) {
  // Entries from before `kind` existed default to a status change.
  return item.kind || 'status_change'
}

function heading(item) {
  switch (kindOf(item)) {
    case 'note':
      return props.audience === 'org' ? `Reply sent by ${item.updated_by}` : `${props.organizationName || 'The organization'} replied`
    case 'internal_note':
      return `Internal note · ${item.updated_by}`
    case 'citizen_reply':
      return props.audience === 'org' ? `Follow-up from ${item.updated_by}` : 'You followed up'
    default:
      return `Status → ${(statusConfig[item.status] || statusConfig.submitted).label}`
  }
}
</script>

<template>
  <div v-if="!timeline.length" class="text-sm text-gray-400 dark:text-gray-500 py-2">
    No updates yet. Every change will appear here — permanently.
  </div>
  <ol v-else class="relative space-y-5">
    <span class="absolute left-[15px] top-2 bottom-2 w-px bg-gray-200 dark:bg-gray-700" aria-hidden="true" />
    <li v-for="item in timeline" :key="item.id ?? item.created_at" class="relative flex items-start gap-3.5">
      <!-- Marker -->
      <span v-if="kindOf(item) === 'status_change'"
        :class="['relative z-10 h-8 w-8 rounded-full ring-4 ring-white dark:ring-gray-800 flex items-center justify-center shrink-0',
          (statusConfig[item.status] || statusConfig.submitted).color]">
        <svg v-if="item.status === 'resolved'" class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
        </svg>
        <svg v-else-if="item.status === 'rejected'" class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12"/>
        </svg>
        <span v-else class="w-2 h-2 bg-white rounded-full" />
      </span>
      <span v-else
        :class="['relative z-10 h-8 w-8 rounded-full ring-4 ring-white dark:ring-gray-800 flex items-center justify-center shrink-0',
          kindOf(item) === 'citizen_reply' ? 'bg-secondary text-white'
          : kindOf(item) === 'internal_note' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'
          : 'bg-primary text-white']">
        <svg v-if="kindOf(item) === 'internal_note'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
        </svg>
        <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
        </svg>
      </span>

      <!-- Body -->
      <div class="min-w-0 flex-1 pt-1">
        <div class="flex items-baseline justify-between gap-2 flex-wrap">
          <p class="text-sm font-semibold text-gray-900 dark:text-white">{{ heading(item) }}</p>
          <time :datetime="item.created_at" class="text-xs text-gray-400 dark:text-gray-500 shrink-0">{{ formatDate(item.created_at) }}</time>
        </div>

        <template v-if="kindOf(item) === 'status_change'">
          <p v-if="item.note" class="mt-1.5 text-sm text-gray-600 dark:text-gray-300 whitespace-pre-line">{{ item.note }}</p>
          <p v-if="item.updated_by" class="mt-0.5 text-xs text-gray-400 dark:text-gray-500">by {{ item.updated_by }}</p>
        </template>
        <div v-else
          :class="['mt-1.5 rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-line',
            kindOf(item) === 'citizen_reply' ? 'bg-secondary/[0.06] dark:bg-secondary/40 text-gray-800 dark:text-gray-100 rounded-tl-sm'
            : kindOf(item) === 'internal_note' ? 'bg-amber-50 dark:bg-amber-900/20 border border-dashed border-amber-300 dark:border-amber-700 text-amber-900 dark:text-amber-100'
            : 'bg-primary/[0.06] dark:bg-primary/15 text-gray-800 dark:text-gray-100 rounded-tl-sm']">
          {{ item.note }}
          <p v-if="kindOf(item) === 'internal_note'" class="mt-1.5 text-[11px] font-semibold uppercase tracking-wide text-amber-600 dark:text-amber-400">
            Only your team can see this
          </p>
        </div>
      </div>
    </li>
  </ol>
</template>
