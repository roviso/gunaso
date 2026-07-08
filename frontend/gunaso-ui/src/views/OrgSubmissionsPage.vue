<script setup>
import { ref, computed, onMounted } from 'vue'
import { useSubmissionStore } from '@/stores/submission'
import { useOrganizationStore } from '@/stores/organization'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import FilterBar from '@/components/FilterBar.vue'
import BulkActions from '@/components/BulkActions.vue'
import SubmissionDetailPanel from '@/components/SubmissionDetailPanel.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import PriorityBadge from '@/components/PriorityBadge.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const submissionStore = useSubmissionStore()
const orgStore = useOrganizationStore()
const authStore = useAuthStore()
const uiStore = useUIStore()

const filters = ref({
  status: '', type: '', priority: '', search: '',
  assignee: '', dateFrom: '', dateTo: '',
})
const selectedIds = ref(new Set())
const activeSubmission = ref(null)

const STATUSES = [
  { value: 'submitted',    label: 'Submitted' },
  { value: 'acknowledged', label: 'Acknowledged' },
  { value: 'in_review',    label: 'In Review' },
  { value: 'resolved',     label: 'Resolved' },
  { value: 'rejected',     label: 'Rejected' },
  { value: 'escalated',    label: 'Escalated' },
  { value: 'closed',       label: 'Closed' },
]

const filtered = computed(() => {
  const f = filters.value
  return submissionStore.orgSubmissions.filter((s) => {
    if (f.status && s.status !== f.status) return false
    if (f.type && s.type !== f.type) return false
    if (f.priority && s.priority !== f.priority) return false
    if (f.assignee === 'unassigned' && s.assigned_to) return false
    if (f.assignee && f.assignee !== 'unassigned' && String(s.assigned_to_id) !== f.assignee) return false
    if (f.search) {
      const q = f.search.toLowerCase()
      if (
        !s.title?.toLowerCase().includes(q) &&
        !s.reference_number?.toLowerCase().includes(q) &&
        !s.submitter_name?.toLowerCase().includes(q)
      ) return false
    }
    if (f.dateFrom && s.created_at < f.dateFrom) return false
    if (f.dateTo && s.created_at > f.dateTo + 'T23:59:59') return false
    return true
  })
})

function clearFilters() {
  filters.value = { status: '', type: '', priority: '', search: '', assignee: '', dateFrom: '', dateTo: '' }
}

function toggleSelect(id) {
  const next = new Set(selectedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedIds.value = next
}

function toggleSelectAll() {
  if (selectedIds.value.size === filtered.value.length && filtered.value.length > 0) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(filtered.value.map((s) => s.id))
  }
}

function openDetail(sub) {
  activeSubmission.value = sub
}

async function handleUpdated(updated) {
  if (updated && activeSubmission.value) {
    activeSubmission.value = { ...activeSubmission.value, ...updated }
  }
  await submissionStore.fetchOrgSubmissions()
}

function exportCSV() {
  const selected = filtered.value.filter((s) => selectedIds.value.has(s.id))
  const rows = [
    ['Reference', 'Title', 'Type', 'Priority', 'Status', 'Submitter', 'Assigned To', 'Date'],
    ...selected.map((s) => [
      s.reference_number,
      s.title,
      s.type,
      s.priority,
      s.status,
      s.is_anonymous ? 'Anonymous' : (s.submitter_name || ''),
      s.assigned_to_name || '',
      s.created_at ? new Date(s.created_at).toLocaleDateString('en-US') : '',
    ])
  ]
  const csv = rows
    .map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(','))
    .join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'submissions.csv'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  uiStore.showSuccess(`Exported ${selected.length} submission${selected.length !== 1 ? 's' : ''}.`)
}

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

const allSelected = computed(
  () => filtered.value.length > 0 && selectedIds.value.size === filtered.value.length
)
const someSelected = computed(
  () => selectedIds.value.size > 0 && selectedIds.value.size < filtered.value.length
)

const typeIcon = { complaint: '⚠️', feedback: '💬', suggestion: '💡' }

onMounted(async () => {
  await submissionStore.fetchOrgSubmissions()
  const slug = orgStore.currentOrg?.slug
  if (slug) await orgStore.fetchStaff(slug)
})
</script>

<template>
  <div class="p-6 space-y-5">
    <h1 class="text-xl font-extrabold text-secondary dark:text-white">Submissions</h1>

    <FilterBar
      v-model="filters"
      :statuses="STATUSES"
      :show-assignee="true"
      :show-date-range="true"
      :staff-list="orgStore.staff"
      :count="filtered.length"
      @clear="clearFilters" />

    <LoadingSpinner v-if="submissionStore.loading" />

    <div v-else class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              <th class="px-4 py-3 w-10">
                <input
                  type="checkbox"
                  :checked="allSelected"
                  :indeterminate="someSelected"
                  @change="toggleSelectAll"
                  class="rounded border-gray-300 dark:border-gray-600 text-primary focus:ring-primary/30" />
              </th>
              <th class="px-4 py-3 text-left">Reference</th>
              <th class="px-4 py-3 text-left">Title / Submitter</th>
              <th class="px-4 py-3 text-left">Type</th>
              <th class="px-4 py-3 text-left">Priority</th>
              <th class="px-4 py-3 text-left">Status</th>
              <th class="px-4 py-3 text-left">Assigned</th>
              <th class="px-4 py-3 text-left">Date</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 dark:divide-gray-700/50">
            <tr v-if="!filtered.length">
              <td colspan="8" class="px-4 py-12 text-center text-gray-400 dark:text-gray-500 text-sm">
                No submissions match the current filters.
              </td>
            </tr>
            <tr
              v-for="sub in filtered"
              :key="sub.id"
              @click.stop="openDetail(sub)"
              class="hover:bg-gray-50 dark:hover:bg-gray-700/30 cursor-pointer transition-colors"
              :class="{ 'bg-primary/5 dark:bg-primary/10': activeSubmission?.id === sub.id }">
              <td class="px-4 py-3" @click.stop>
                <input
                  type="checkbox"
                  :checked="selectedIds.has(sub.id)"
                  @change="toggleSelect(sub.id)"
                  class="rounded border-gray-300 dark:border-gray-600 text-primary focus:ring-primary/30" />
              </td>
              <td class="px-4 py-3 whitespace-nowrap">
                <span class="font-mono text-xs bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 px-2 py-0.5 rounded">
                  {{ sub.reference_number }}
                </span>
              </td>
              <td class="px-4 py-3 max-w-[220px]">
                <p class="font-medium text-gray-900 dark:text-white truncate flex items-center gap-1.5">
                  <span>{{ typeIcon[sub.type] || '📋' }}</span>
                  {{ sub.title }}
                </p>
                <p class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                  {{ sub.is_anonymous ? 'Anonymous' : (sub.submitter_name || '—') }}
                </p>
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
                {{ sub.assigned_to_name || '—' }}
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-xs text-gray-500 dark:text-gray-400">
                {{ formatDate(sub.created_at) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Bulk action bar (floats at bottom) -->
    <BulkActions
      :selected-count="selectedIds.size"
      @change-status="uiStore.showInfo('Select a status from the detail panel for each submission.')"
      @export-csv="exportCSV"
      @deselect-all="selectedIds = new Set()" />

    <!-- Slide-in detail panel -->
    <SubmissionDetailPanel
      :submission="activeSubmission"
      @close="activeSubmission = null"
      @updated="handleUpdated" />
  </div>
</template>
