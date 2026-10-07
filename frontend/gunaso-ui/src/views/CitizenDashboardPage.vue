<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useSubmissionStore } from '@/stores/submission'
import StatusBadge from '@/components/StatusBadge.vue'
import PriorityBadge from '@/components/PriorityBadge.vue'
import SubmissionTimeline from '@/components/SubmissionTimeline.vue'
import StatusProgress from '@/components/StatusProgress.vue'

const authStore = useAuthStore()
const submissionStore = useSubmissionStore()

const selectedSubmission = ref(null)
const filterKey = ref('all')

// Grouped filters over the real backend status vocabulary.
const ACTIVE_STATUSES = ['submitted', 'acknowledged', 'in_review', 'escalated']
const filters = [
  { key: 'all', label: 'All', match: () => true },
  { key: 'active', label: 'Active', match: (s) => ACTIVE_STATUSES.includes(s.status) },
  { key: 'resolved', label: 'Resolved', match: (s) => s.status === 'resolved' },
  { key: 'rejected', label: 'Rejected', match: (s) => s.status === 'rejected' },
  { key: 'closed', label: 'Closed', match: (s) => s.status === 'closed' },
]

const filtered = computed(() => {
  const f = filters.find((x) => x.key === filterKey.value) || filters[0]
  return submissionStore.submissions.filter(f.match)
})

function countFor(filter) {
  return submissionStore.submissions.filter(filter.match).length
}

const stats = computed(() => {
  const subs = submissionStore.submissions
  return [
    { label: 'Total', value: subs.length, accent: 'text-secondary dark:text-white' },
    { label: 'Active', value: subs.filter((s) => ACTIVE_STATUSES.includes(s.status)).length, accent: 'text-blue-600 dark:text-blue-400' },
    { label: 'Escalated', value: subs.filter((s) => s.status === 'escalated').length, accent: 'text-orange-600 dark:text-orange-400' },
    { label: 'Resolved', value: subs.filter((s) => s.status === 'resolved').length, accent: 'text-green-600 dark:text-green-400' },
  ]
})

// What needs the citizen's action: the organization spoke last, or the case
// has an outcome that hasn't been rated yet.
function lastPublicEntry(sub) {
  const entries = (sub.timeline || []).filter((e) => e.kind !== 'internal_note')
  return entries[entries.length - 1]
}

const attention = computed(() => submissionStore.submissions.flatMap((sub) => {
  const last = lastPublicEntry(sub)
  if (['resolved', 'rejected', 'closed'].includes(sub.status) && !sub.satisfaction_score) {
    return [{ sub, kind: 'rate', text: `${sub.organization_name} marked this ${sub.status === 'rejected' ? 'rejected' : 'resolved'} — how did they do?`, cta: 'Rate the outcome' }]
  }
  if (last && (last.kind === 'note' || (last.kind === 'status_change' && last.note)) && sub.status !== 'closed') {
    return [{ sub, kind: 'reply', text: `${sub.organization_name} replied: “${last.note.length > 90 ? last.note.slice(0, 90) + '…' : last.note}”`, cta: 'Open & reply' }]
  }
  return []
}))

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
})

const typeIcons = {
  complaint: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
  feedback: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z',
  suggestion: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z',
}

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

onMounted(() => submissionStore.fetchMySubmissions())
</script>

<template>
  <div class="bg-app-bg dark:bg-gray-900 min-h-screen">
    <!-- Header -->
    <div class="bg-white dark:bg-gray-800 border-b border-gray-100 dark:border-gray-700">
      <div class="page-container py-6">
        <div class="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h1 class="font-display text-2xl font-bold text-secondary dark:text-white">
              {{ greeting }}, {{ (authStore.user?.name || 'Citizen').split(' ')[0] }}
            </h1>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              Here's where all your submissions stand.
            </p>
          </div>
          <RouterLink to="/submit" class="btn-primary text-sm">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
            </svg>
            File a gunaso
          </RouterLink>
        </div>

        <!-- Stat tiles -->
        <div v-if="submissionStore.submissions.length" class="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 stagger">
          <div v-for="stat in stats" :key="stat.label"
            class="rounded-xl border border-gray-100 dark:border-gray-700 bg-app-bg/60 dark:bg-gray-900/40 px-4 py-3">
            <p :class="['font-display text-2xl font-bold tabular-nums', stat.accent]">{{ stat.value }}</p>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{{ stat.label }}</p>
          </div>
        </div>
      </div>
    </div>

    <div class="page-container py-8">
      <!-- Needs your attention -->
      <div v-if="attention.length" class="mb-6 card p-5 border-primary/20 bg-primary/[0.03] dark:bg-primary/10 animate-fade-up">
        <h2 class="font-display font-bold text-secondary dark:text-white text-sm mb-3 flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-primary animate-pulse-dot" /> Needs your attention
        </h2>
        <ul class="space-y-2">
          <li v-for="item in attention.slice(0, 5)" :key="item.sub.id"
            class="flex items-center gap-3 flex-wrap sm:flex-nowrap p-3 rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700">
            <span class="text-lg" aria-hidden="true">{{ item.kind === 'rate' ? '⭐' : '💬' }}</span>
            <div class="min-w-0 flex-1">
              <p class="text-sm font-semibold text-gray-900 dark:text-white truncate">{{ item.sub.title }}</p>
              <p class="text-xs text-gray-500 dark:text-gray-400 truncate">{{ item.text }}</p>
            </div>
            <RouterLink :to="{ name: 'Track', params: { ref: item.sub.reference_number } }" class="btn-primary !py-2 !px-4 text-xs shrink-0">
              {{ item.cta }}
            </RouterLink>
          </li>
        </ul>
      </div>

      <div class="flex flex-col lg:flex-row gap-6">
        <!-- List panel -->
        <div class="flex-1 min-w-0">
          <!-- Status filters -->
          <div class="flex gap-2 mb-5 overflow-x-auto pb-1" role="tablist" aria-label="Filter submissions by status">
            <button v-for="f in filters" :key="f.key"
              role="tab" :aria-selected="filterKey === f.key"
              @click="filterKey = f.key; selectedSubmission = null"
              :class="['px-3.5 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all duration-150 shrink-0',
                filterKey === f.key
                  ? 'bg-secondary dark:bg-white text-white dark:text-secondary'
                  : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:border-secondary dark:hover:border-gray-500']">
              {{ f.label }}
              <span v-if="f.key !== 'all'" class="ml-1 opacity-60 tabular-nums">({{ countFor(f) }})</span>
            </button>
          </div>

          <!-- Skeletons -->
          <div v-if="submissionStore.loading" class="space-y-3">
            <div v-for="i in 4" :key="i" class="card p-4">
              <div class="flex items-start gap-3 mb-3">
                <div class="skeleton w-9 h-9 rounded-lg" />
                <div class="flex-1 space-y-2">
                  <div class="skeleton h-4 w-3/4" />
                  <div class="skeleton h-3 w-1/3" />
                </div>
                <div class="skeleton h-6 w-20 rounded-full" />
              </div>
              <div class="skeleton h-3 w-1/2" />
            </div>
          </div>

          <!-- Empty state -->
          <div v-else-if="!filtered.length && !submissionStore.submissions.length" class="card p-10 text-center animate-fade-up">
            <div class="w-16 h-16 rounded-3xl bg-primary/10 dark:bg-primary/15 flex items-center justify-center mx-auto mb-5">
              <svg class="w-7 h-7 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z"/>
              </svg>
            </div>
            <h3 class="font-display font-bold text-secondary dark:text-white text-lg mb-1.5">Your voice starts here</h3>
            <p class="text-gray-500 dark:text-gray-400 text-sm max-w-sm mx-auto mb-6 leading-relaxed">
              File your first complaint, feedback, or suggestion — it takes under two minutes,
              and you'll be able to track every step right here.
            </p>
            <div class="flex flex-wrap justify-center gap-3">
              <RouterLink to="/submit" class="btn-primary text-sm">Submit your first complaint</RouterLink>
              <RouterLink to="/organizations" class="btn-secondary text-sm">Browse organizations</RouterLink>
            </div>
          </div>

          <!-- No matches for the current filter -->
          <div v-else-if="!filtered.length" class="text-center py-16 card">
            <p class="text-gray-500 dark:text-gray-400 font-medium">No submissions match this filter</p>
            <button @click="filterKey = 'all'" class="mt-3 text-primary text-sm font-medium hover:underline">Show all</button>
          </div>

          <!-- Submission list -->
          <div v-else class="space-y-3">
            <div v-for="sub in filtered" :key="sub.id"
              @click="selectedSubmission = selectedSubmission?.id === sub.id ? null : sub"
              @keydown.enter.prevent="selectedSubmission = selectedSubmission?.id === sub.id ? null : sub"
              tabindex="0" role="button"
              :aria-expanded="selectedSubmission?.id === sub.id"
              class="card-interactive p-4"
              :class="{ 'ring-2 ring-primary/30 border-primary/30': selectedSubmission?.id === sub.id }">
              <div class="flex items-start gap-3 mb-3">
                <span class="w-9 h-9 rounded-lg bg-gray-100 dark:bg-gray-700 flex items-center justify-center shrink-0 mt-0.5">
                  <svg class="w-5 h-5 text-gray-500 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" :d="typeIcons[sub.type] || typeIcons.complaint"/>
                  </svg>
                </span>
                <div class="flex-1 min-w-0">
                  <p class="font-semibold text-gray-900 dark:text-white text-sm line-clamp-2">{{ sub.title }}</p>
                  <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{{ sub.organization_name }}</p>
                </div>
                <StatusBadge :status="sub.status" />
              </div>
              <div class="mb-3 px-1">
                <StatusProgress :status="sub.status" :timeline="sub.timeline || []" compact />
              </div>
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-xs font-mono text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-700/50 px-2 py-0.5 rounded">{{ sub.reference_number }}</span>
                <span v-if="sub.satisfaction_score" class="text-xs font-bold text-amber-500">★ {{ sub.satisfaction_score }}/5</span>
                <PriorityBadge :priority="sub.priority" />
                <span class="text-xs text-gray-400 dark:text-gray-500 ml-auto">{{ formatDate(sub.created_at) }}</span>
              </div>

              <!-- Expanded timeline -->
              <Transition name="slide">
                <div v-if="selectedSubmission?.id === sub.id" class="mt-5 pt-5 border-t border-gray-100 dark:border-gray-700" @click.stop>
                  <p class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">Case history</p>
                  <SubmissionTimeline :timeline="sub.timeline || []" :organization-name="sub.organization_name" />
                  <div class="mt-5">
                    <RouterLink :to="{ name: 'Track', params: { ref: sub.reference_number } }"
                      class="btn-secondary !py-2 !px-4 text-xs">
                      Open case — reply or rate →
                    </RouterLink>
                  </div>
                </div>
              </Transition>
            </div>
          </div>
        </div>

        <!-- Sidebar info -->
        <div class="w-full lg:w-72 shrink-0 space-y-4">
          <div class="card p-5">
            <h3 class="font-display font-bold text-gray-900 dark:text-white mb-4 text-sm">Status breakdown</h3>
            <div class="space-y-3">
              <div v-for="status in ['submitted', 'acknowledged', 'in_review', 'escalated', 'resolved', 'rejected', 'closed']"
                :key="status" class="flex items-center justify-between">
                <StatusBadge :status="status" />
                <span class="text-sm font-bold text-secondary dark:text-white tabular-nums">
                  {{ submissionStore.submissions.filter(x => x.status === status).length }}
                </span>
              </div>
            </div>
          </div>

          <div class="card p-5 bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20">
            <h4 class="font-display font-bold text-gray-900 dark:text-white text-sm mb-2">Track by Reference</h4>
            <p class="text-xs text-gray-500 dark:text-gray-400 mb-3">Have a reference number? Track it anonymously.</p>
            <RouterLink :to="{ name: 'Track' }" class="btn-primary w-full py-2 text-xs justify-center">Go to Track Page</RouterLink>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.slide-enter-active, .slide-leave-active { transition: all 0.2s ease; }
.slide-enter-from, .slide-leave-to { opacity: 0; transform: translateY(-6px); }
</style>
