<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useSubmissionStore } from '@/stores/submission'
import { useUIStore } from '@/stores/ui'
import StatusBadge from '@/components/StatusBadge.vue'
import PriorityBadge from '@/components/PriorityBadge.vue'
import StatsCard from '@/components/StatsCard.vue'
import SubmissionTimeline from '@/components/SubmissionTimeline.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const authStore = useAuthStore()
const submissionStore = useSubmissionStore()
const uiStore = useUIStore()

const filters = ref({ status: '', type: '', priority: '', search: '' })
const showDetailModal = ref(false)
const showStatusModal = ref(false)
const selectedSubmission = ref(null)
const statusUpdate = ref({ status: '', note: '' })
const updatingStatus = ref(false)

const statuses = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'in_review', label: 'In Review' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'closed', label: 'Closed' },
  { value: 'rejected', label: 'Rejected' },
]

const filtered = computed(() => {
  return submissionStore.orgSubmissions.filter((s) => {
    if (filters.value.status && s.status !== filters.value.status) return false
    if (filters.value.type && s.type !== filters.value.type) return false
    if (filters.value.priority && s.priority !== filters.value.priority) return false
    if (filters.value.search) {
      const q = filters.value.search.toLowerCase()
      return s.title?.toLowerCase().includes(q) || s.reference_number?.toLowerCase().includes(q) || s.submitter_name?.toLowerCase().includes(q)
    }
    return true
  })
})

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function openDetail(sub) {
  selectedSubmission.value = sub
  showDetailModal.value = true
}

function openStatusUpdate(sub) {
  selectedSubmission.value = sub
  statusUpdate.value = { status: sub.status, note: '' }
  showStatusModal.value = true
  showDetailModal.value = false
}

async function submitStatusUpdate() {
  if (!statusUpdate.value.status) return
  updatingStatus.value = true
  try {
    await submissionStore.updateStatus(selectedSubmission.value.id, statusUpdate.value)
    uiStore.showSuccess('Status updated successfully!')
    showStatusModal.value = false
    selectedSubmission.value = null
  } catch {
    uiStore.showError('Failed to update status. Please try again.')
  } finally {
    updatingStatus.value = false
  }
}

function clearFilters() {
  filters.value = { status: '', type: '', priority: '', search: '' }
}

const typeIcon = { complaint: '⚠️', feedback: '💬', suggestion: '💡' }

onMounted(async () => {
  await Promise.all([
    submissionStore.fetchOrgSubmissions(),
    submissionStore.fetchOrgStats()
  ])
})
</script>

<template>
  <div class="bg-app-bg dark:bg-gray-900 min-h-screen">
    <!-- Header -->
    <div class="bg-white dark:bg-gray-800 border-b border-gray-100 dark:border-gray-700">
      <div class="page-container py-6">
        <div class="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h1 class="text-2xl font-extrabold text-secondary dark:text-white">Organization Dashboard</h1>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              Manage submissions for <span class="font-semibold">{{ authStore.user?.organization_name || 'Your Organization' }}</span>
            </p>
          </div>
          <RouterLink to="/organizations" class="btn-ghost text-sm">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
            </svg>
            Public View
          </RouterLink>
        </div>
      </div>
    </div>

    <div class="page-container py-6 space-y-6">
      <!-- Stats Row -->
      <div v-if="submissionStore.orgStats" class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard label="Total Submissions" :value="submissionStore.orgStats.total" icon="📋" color="primary" />
        <StatsCard label="Pending" :value="submissionStore.orgStats.pending" icon="⏳" color="orange" sub="Needs attention" />
        <StatsCard label="In Review" :value="submissionStore.orgStats.in_review" icon="🔍" color="blue" />
        <StatsCard label="Resolved This Month" :value="submissionStore.orgStats.resolved_month" icon="✅" color="green"
          :sub="`Avg ${submissionStore.orgStats.avg_resolution_days} days`" />
      </div>

      <!-- Filters & Search -->
      <div class="card p-4">
        <div class="flex flex-wrap gap-3 items-center">
          <input v-model="filters.search" type="text" placeholder="Search by title, reference..."
            class="input-base max-w-xs" />

          <select v-model="filters.status" class="input-base w-auto min-w-[140px]">
            <option v-for="s in statuses" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>

          <select v-model="filters.type" class="input-base w-auto min-w-[130px]">
            <option value="">All Types</option>
            <option value="complaint">Complaint</option>
            <option value="feedback">Feedback</option>
            <option value="suggestion">Suggestion</option>
          </select>

          <select v-model="filters.priority" class="input-base w-auto min-w-[130px]">
            <option value="">All Priorities</option>
            <option value="urgent">Urgent</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          <button v-if="filters.search || filters.status || filters.type || filters.priority"
            @click="clearFilters" class="btn-ghost text-sm text-red-500 hover:text-red-600 dark:text-red-400">
            Clear filters
          </button>

          <span class="ml-auto text-sm text-gray-500 dark:text-gray-400">
            <span class="font-semibold text-gray-900 dark:text-white">{{ filtered.length }}</span> submissions
          </span>
        </div>
      </div>

      <!-- Table -->
      <LoadingSpinner v-if="submissionStore.loading" />

      <div v-else class="card overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
                <th class="text-left px-4 py-3 font-semibold text-gray-600 dark:text-gray-300 text-xs uppercase tracking-wider">Reference</th>
                <th class="text-left px-4 py-3 font-semibold text-gray-600 dark:text-gray-300 text-xs uppercase tracking-wider">Title</th>
                <th class="text-left px-4 py-3 font-semibold text-gray-600 dark:text-gray-300 text-xs uppercase tracking-wider">Type</th>
                <th class="text-left px-4 py-3 font-semibold text-gray-600 dark:text-gray-300 text-xs uppercase tracking-wider">Priority</th>
                <th class="text-left px-4 py-3 font-semibold text-gray-600 dark:text-gray-300 text-xs uppercase tracking-wider">Status</th>
                <th class="text-left px-4 py-3 font-semibold text-gray-600 dark:text-gray-300 text-xs uppercase tracking-wider">Date</th>
                <th class="text-left px-4 py-3 font-semibold text-gray-600 dark:text-gray-300 text-xs uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100 dark:divide-gray-700/50">
              <tr v-if="!filtered.length">
                <td colspan="7" class="px-4 py-12 text-center text-gray-400 dark:text-gray-500 text-sm">
                  No submissions match the current filters.
                </td>
              </tr>
              <tr v-for="sub in filtered" :key="sub.id"
                class="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
                <td class="px-4 py-3 whitespace-nowrap">
                  <span class="font-mono text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
                    {{ sub.reference_number }}
                  </span>
                </td>
                <td class="px-4 py-3">
                  <div class="flex items-center gap-2">
                    <span>{{ typeIcon[sub.type] || '📋' }}</span>
                    <span class="font-medium text-gray-900 dark:text-white max-w-[200px] truncate">{{ sub.title }}</span>
                  </div>
                  <p v-if="sub.submitter_name" class="text-xs text-gray-400 dark:text-gray-500 mt-0.5 pl-5">{{ sub.submitter_name }}</p>
                </td>
                <td class="px-4 py-3 whitespace-nowrap">
                  <span class="capitalize text-xs font-medium text-gray-600 dark:text-gray-400">{{ sub.type }}</span>
                </td>
                <td class="px-4 py-3 whitespace-nowrap">
                  <PriorityBadge :priority="sub.priority" />
                </td>
                <td class="px-4 py-3 whitespace-nowrap">
                  <StatusBadge :status="sub.status" />
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-xs text-gray-500 dark:text-gray-400">
                  {{ formatDate(sub.created_at) }}
                </td>
                <td class="px-4 py-3 whitespace-nowrap">
                  <div class="flex items-center gap-1">
                    <button @click="openDetail(sub)"
                      class="p-1.5 rounded-lg text-gray-400 hover:text-secondary dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors" title="View details">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                      </svg>
                    </button>
                    <button @click="openStatusUpdate(sub)"
                      class="p-1.5 rounded-lg text-gray-400 hover:text-primary hover:bg-primary/10 transition-colors" title="Update status">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ===== DETAIL MODAL ===== -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showDetailModal && selectedSubmission" class="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showDetailModal = false" />
          <div class="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-2xl border border-gray-100 dark:border-gray-700 overflow-hidden max-h-[90vh] flex flex-col">
            <!-- Header -->
            <div class="flex items-start justify-between p-6 pb-4 border-b border-gray-100 dark:border-gray-700">
              <div>
                <div class="flex items-center gap-2 mb-1">
                  <span class="font-mono text-xs text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">{{ selectedSubmission.reference_number }}</span>
                  <StatusBadge :status="selectedSubmission.status" />
                  <PriorityBadge :priority="selectedSubmission.priority" />
                </div>
                <h2 class="text-lg font-bold text-gray-900 dark:text-white">{{ selectedSubmission.title }}</h2>
                <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                  {{ selectedSubmission.submitter_name || 'Anonymous' }} · {{ formatDate(selectedSubmission.created_at) }}
                </p>
              </div>
              <button @click="showDetailModal = false" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 p-1 shrink-0">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>

            <!-- Body -->
            <div class="flex-1 overflow-y-auto p-6 space-y-5">
              <div>
                <p class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">Description</p>
                <p class="text-sm text-gray-700 dark:text-gray-300 leading-relaxed bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4">
                  {{ selectedSubmission.description }}
                </p>
              </div>

              <div>
                <p class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">Status History</p>
                <SubmissionTimeline :timeline="selectedSubmission.timeline || []" />
              </div>
            </div>

            <!-- Footer -->
            <div class="p-4 border-t border-gray-100 dark:border-gray-700 flex gap-3">
              <button @click="showDetailModal = false" class="btn-secondary flex-1 py-2.5 text-sm">Close</button>
              <button @click="openStatusUpdate(selectedSubmission)" class="btn-primary flex-1 py-2.5 text-sm">Update Status</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- ===== STATUS UPDATE MODAL ===== -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showStatusModal && selectedSubmission" class="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showStatusModal = false" />
          <div class="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-md border border-gray-100 dark:border-gray-700">
            <div class="p-6">
              <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-1">Update Submission Status</h2>
              <p class="text-sm text-gray-500 dark:text-gray-400 mb-5 line-clamp-1">{{ selectedSubmission.title }}</p>

              <div class="space-y-4">
                <div>
                  <label class="label">New Status *</label>
                  <select v-model="statusUpdate.status" class="input-base">
                    <option value="">Select new status</option>
                    <option value="pending">Pending</option>
                    <option value="in_review">In Review</option>
                    <option value="resolved">Resolved</option>
                    <option value="closed">Closed</option>
                    <option value="rejected">Rejected</option>
                  </select>
                </div>

                <div>
                  <label class="label">Response Note (optional)</label>
                  <textarea v-model="statusUpdate.note" rows="3" placeholder="Add a note to the citizen explaining the status change..."
                    class="input-base resize-none" maxlength="500" />
                  <p class="text-xs text-gray-400 dark:text-gray-500 mt-1 text-right">{{ statusUpdate.note.length }}/500</p>
                </div>
              </div>
            </div>

            <div class="px-6 pb-6 flex gap-3">
              <button @click="showStatusModal = false" :disabled="updatingStatus" class="btn-secondary flex-1 py-2.5 text-sm">Cancel</button>
              <button @click="submitStatusUpdate" :disabled="!statusUpdate.status || updatingStatus" class="btn-primary flex-1 py-2.5 text-sm disabled:opacity-50">
                <svg v-if="updatingStatus" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                {{ updatingStatus ? 'Saving...' : 'Update Status' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: all 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>
