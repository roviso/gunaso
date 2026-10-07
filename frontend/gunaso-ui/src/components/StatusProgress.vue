<script setup>
import { computed } from 'vue'

// A citizen-friendly, at-a-glance view of where a case is in the lifecycle
// (backend VALID_TRANSITIONS, CLAUDE.md §5) — the detailed audit trail stays
// in SubmissionTimeline. Skipped steps (e.g. submitted → in_review directly)
// still count as passed.
const props = defineProps({
  status: { type: String, required: true },
  timeline: { type: Array, default: () => [] },
  // Creation doesn't write a timeline entry, so "Submitted" is dated from here.
  createdAt: { type: String, default: '' },
  compact: { type: Boolean, default: false },
})

const STAGE_OF = {
  submitted: 0, acknowledged: 1, in_review: 2, escalated: 2, resolved: 3, rejected: 3, closed: 4,
}

const rejected = computed(() =>
  props.status === 'rejected' || props.timeline.some((e) => e.status === 'rejected')
)

const firstReached = computed(() => {
  const seen = props.createdAt ? { 0: props.createdAt } : {}
  for (const entry of props.timeline) {
    if (entry.kind && entry.kind !== 'status_change') continue
    const stage = STAGE_OF[entry.status]
    if (stage != null && !seen[stage]) seen[stage] = entry.created_at
  }
  return seen
})

const current = computed(() => STAGE_OF[props.status] ?? 0)

const steps = computed(() => [
  { label: 'Submitted' },
  { label: 'Acknowledged' },
  { label: props.status === 'escalated' ? 'Escalated' : 'In review' },
  { label: rejected.value ? 'Rejected' : 'Resolved', outcome: true },
  { label: 'Closed' },
].map((step, i) => ({
  ...step,
  state: i < current.value ? 'done' : i === current.value ? 'current' : 'todo',
  date: firstReached.value[i],
})))

function shortDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function dotClass(step) {
  if (step.state === 'todo') return 'bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-600'
  if (step.outcome && rejected.value) return 'bg-red-500 text-white'
  if (step.state === 'current' && props.status === 'escalated') return 'bg-orange-500 text-white'
  if (step.state === 'current' && current.value < 3) return 'bg-primary text-white ring-4 ring-primary/15'
  return 'bg-green-500 text-white'
}
</script>

<template>
  <ol :class="['flex items-start w-full', compact ? 'gap-0' : '']" aria-label="Case progress">
    <li v-for="(step, i) in steps" :key="i" class="relative flex-1 flex flex-col items-center text-center min-w-0"
      :aria-current="step.state === 'current' ? 'step' : undefined">
      <span v-if="i > 0"
        :class="['absolute top-[13px] right-1/2 w-full h-0.5 -z-0',
          step.state !== 'todo' ? (rejected && step.outcome ? 'bg-red-300' : 'bg-green-400') : 'bg-gray-200 dark:bg-gray-700']" />
      <span :class="['relative z-10 w-7 h-7 rounded-full flex items-center justify-center transition-all', dotClass(step)]">
        <svg v-if="step.state === 'done' || (step.state === 'current' && i >= 3)" class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path v-if="step.outcome && rejected" stroke-linecap="round" stroke-width="3" d="M6 18L18 6M6 6l12 12"/>
          <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/>
        </svg>
        <span v-else-if="step.state === 'current'" class="w-2 h-2 rounded-full bg-white animate-pulse-dot" />
      </span>
      <span :class="['mt-2 font-semibold leading-tight', compact ? 'text-[10px]' : 'text-[11px] sm:text-xs',
        step.state === 'todo' ? 'text-gray-400 dark:text-gray-500' : 'text-gray-800 dark:text-gray-100']">
        {{ step.label }}
      </span>
      <span v-if="!compact && step.date" class="text-[10px] text-gray-400 dark:text-gray-500 mt-0.5">{{ shortDate(step.date) }}</span>
    </li>
  </ol>
</template>
