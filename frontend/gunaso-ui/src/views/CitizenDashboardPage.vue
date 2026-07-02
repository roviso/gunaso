<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useSubmissionStore } from '@/stores/submission'
import StatusBadge from '@/components/StatusBadge.vue'
import PriorityBadge from '@/components/PriorityBadge.vue'
import SubmissionTimeline from '@/components/SubmissionTimeline.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const authStore = useAuthStore()
const submissionStore = useSubmissionStore()

const selectedSubmission = ref(null)
const filterStatus = ref('all')

const statuses = [
  { value: 'all', label: 'All' },
  { value: 'pending', label: 'Pending' },
  { value: 'in_review', label: 'In Review' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'closed', label: 'Closed' },
]

const filtered = computed(() => {
  if (filterStatus.value === 'all') return submissionStore.submissions
  return submissionStore.submissions.filter((s) => s.status === filterStatus.value)
})

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

const typeIcon = { complaint: '⚠️', feedback: '💬', suggestion: '💡' }

onMounted(() => submissionStore.fetchMySubmissions())
</script>

<template>
  <div class="bg-app-bg dark:bg-gray-900 min-h-screen">
    <!-- Header -->
    <div class="bg-white dark:bg-gray-800 border-b border-gray-100 dark:border-gray-700">
      <div class="page-container py-6">
        <div class="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h1 class="text-2xl font-extrabold text-secondary dark:text-white">My Submissions</h1>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              Welcome back, <span class="font-semibold">{{ authStore.user?.name || 'Citizen' }}</span>
            </p>
          </div>
          <RouterLink to="/submit" class="btn-primary text-sm">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
            </svg>
            New Complaint
          </RouterLink>
        </div>
      </div>
    </div>

    <div class="page-container py-8">
      <div class="flex flex-col lg:flex-row gap-6">
        <!-- List panel -->
        <div class="flex-1 min-w-0">
          <!-- Status filters -->
          <div class="flex gap-2 mb-5 overflow-x-auto pb-1">
            <button v-for="s in statuses" :key="s.value"
              @click="filterStatus = s.value; selectedSubmission = null"
              :class="['px-3.5 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all duration-150 shrink-0',
                filterStatus === s.value
                  ? 'bg-secondary dark:bg-white text-white dark:text-secondary'
                  : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:border-secondary dark:hover:border-gray-500']">
              {{ s.label }}
              <span v-if="s.value !== 'all'" class="ml-1 opacity-60">
                ({{ submissionStore.submissions.filter(x => x.status === s.value).length }})
              </span>
            </button>
          </div>

          <LoadingSpinner v-if="submissionStore.loading" />

          <div v-else-if="!filtered.length" class="text-center py-16 card">
            <svg class="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
            <p class="text-gray-500 dark:text-gray-400 font-medium">No submissions yet</p>
            <RouterLink to="/submit" class="mt-4 text-primary text-sm font-medium hover:underline inline-block">Submit your first complaint →</RouterLink>
          </div>

          <div v-else class="space-y-3">
            <div v-for="sub in filtered" :key="sub.id"
              @click="selectedSubmission = selectedSubmission?.id === sub.id ? null : sub"
              class="card p-4 cursor-pointer hover:shadow-md transition-all duration-200"
              :class="{ 'ring-2 ring-primary/30 border-primary/30': selectedSubmission?.id === sub.id }">
              <div class="flex items-start gap-3 mb-3">
                <span class="text-lg mt-0.5">{{ typeIcon[sub.type] || '📋' }}</span>
                <div class="flex-1 min-w-0">
                  <p class="font-semibold text-gray-900 dark:text-white text-sm line-clamp-2">{{ sub.title }}</p>
                  <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{{ sub.organization_name }}</p>
                </div>
                <StatusBadge :status="sub.status" />
              </div>
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-xs font-mono text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-700/50 px-2 py-0.5 rounded">{{ sub.reference_number }}</span>
                <PriorityBadge :priority="sub.priority" />
                <span class="text-xs text-gray-400 dark:text-gray-500 ml-auto">{{ formatDate(sub.created_at) }}</span>
              </div>

              <!-- Expanded timeline -->
              <Transition name="slide">
                <div v-if="selectedSubmission?.id === sub.id" class="mt-5 pt-5 border-t border-gray-100 dark:border-gray-700">
                  <p class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">Status History</p>
                  <SubmissionTimeline :timeline="sub.timeline || []" />
                  <div class="mt-4">
                    <RouterLink :to="{ name: 'Track', query: { ref: sub.reference_number } }"
                      class="text-xs text-primary font-medium hover:underline flex items-center gap-1">
                      View full tracking page →
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
            <h3 class="font-bold text-gray-900 dark:text-white mb-4 text-sm">Summary</h3>
            <div class="space-y-3">
              <div v-for="s in statuses.slice(1)" :key="s.value" class="flex items-center justify-between">
                <span class="text-sm text-gray-600 dark:text-gray-400">{{ s.label }}</span>
                <span class="text-sm font-bold text-secondary dark:text-white">
                  {{ submissionStore.submissions.filter(x => x.status === s.value).length }}
                </span>
              </div>
              <div class="border-t border-gray-100 dark:border-gray-700 pt-3 flex items-center justify-between">
                <span class="text-sm font-semibold text-gray-700 dark:text-gray-300">Total</span>
                <span class="text-sm font-extrabold text-secondary dark:text-white">{{ submissionStore.submissions.length }}</span>
              </div>
            </div>
          </div>

          <div class="card p-5 bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20">
            <h4 class="font-bold text-gray-900 dark:text-white text-sm mb-2">Track by Reference</h4>
            <p class="text-xs text-gray-500 dark:text-gray-400 mb-3">Have a reference number? Track it anonymously.</p>
            <RouterLink to="/track" class="btn-primary w-full py-2 text-xs justify-center">Go to Track Page</RouterLink>
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
