<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
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
import { submissionsAPI } from '@/api/submissions'
import { apiErrorMessage } from '@/api/index'

const route = useRoute()
const router = useRouter()
const submissionStore = useSubmissionStore()
const orgStore = useOrganizationStore()
const authStore = useAuthStore()
const uiStore = useUIStore()

const filters = ref({
  status: '', type: '', priority: '', search: '',
  assignee: '', branch: '', category: '', dateFrom: '', dateTo: '',
})

// Seed filters from the URL so dashboard cards can deep-link into filtered views
// (e.g. /org/submissions?status=submitted,acknowledged or ?assignee=unassigned).
for (const key of Object.keys(filters.value)) {
  if (typeof route.query[key] === 'string') filters.value[key] = route.query[key]
}
const selectedIds = ref(new Set())
const activeSubmission = ref(null)

// Work queues — resolved server-side (see OrgAdminSubmissionsView /
// _apply_queue_filters) so they're correct beyond the first page.
const QUEUES = [
  { key: 'open', label: 'Open', params: { open: 'true' } },
  { key: 'overdue', label: '⏰ Overdue', params: { overdue: 'true' } },
  { key: 'waiting', label: '💬 Citizen waiting', params: { awaiting_reply: 'true' } },
  { key: 'unassigned', label: 'Unassigned', params: { assigned_to: 'none', open: 'true' } },
  { key: 'mine', label: 'Assigned to me', params: { assigned_to: 'me' } },
  { key: 'all', label: 'All', params: {} },
]
const PAGE_SIZE = 100
const queue = ref(QUEUES.some((q) => q.key === route.query.queue) ? route.query.queue : 'all')
const queueParams = computed(() => QUEUES.find((q) => q.key === queue.value)?.params || {})
const exporting = ref(false)

function loadQueue() {
  selectedIds.value = new Set()
  return submissionStore.fetchOrgSubmissions({ page_size: PAGE_SIZE, ...queueParams.value })
}

watch(queue, (q) => {
  router.replace({ query: { ...route.query, queue: q === 'all' ? undefined : q } })
  loadQueue()
})

// Full, server-side export of the current queue + the filters the API
// understands. Unlike the selection export below, this isn't capped to the
// rows loaded on screen and applies the backend's anonymity/contact rules.
async function exportAll() {
  if (exporting.value) return
  exporting.value = true
  try {
    const f = filters.value
    const params = {
      ...queueParams.value,
      ...(f.status && !f.status.includes(',') ? { status: f.status } : {}),
      ...(f.type ? { submission_type: f.type } : {}),
      ...(f.priority ? { priority: f.priority } : {}),
      ...(f.branch ? { branch: f.branch } : {}),
      ...(f.search ? { search: f.search } : {}),
    }
    const { data, headers } = await submissionsAPI.exportCsv(params)
    const match = /filename="([^"]+)"/.exec(headers['content-disposition'] || '')
    const url = URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = url
    a.download = match ? match[1] : 'gunaso-submissions.csv'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
    uiStore.showSuccess('Export downloaded.')
  } catch (err) {
    uiStore.showError(apiErrorMessage(err, 'Export failed.'))
  } finally {
    exporting.value = false
  }
}

const BASE_STATUSES = [
  { value: 'submitted',    label: 'Submitted' },
  { value: 'acknowledged', label: 'Acknowledged' },
  { value: 'in_review',    label: 'In Review' },
  { value: 'resolved',     label: 'Resolved' },
  { value: 'rejected',     label: 'Rejected' },
  { value: 'escalated',    label: 'Escalated' },
  { value: 'closed',       label: 'Closed' },
]

// Dashboard links can filter on several statuses at once ("submitted,acknowledged");
// surface such a value as its own option so the select reflects the active filter.
const STATUSES = computed(() => {
  const current = filters.value.status
  if (!current || !current.includes(',')) return BASE_STATUSES
  const label = current
    .split(',')
    .map((v) => BASE_STATUSES.find((s) => s.value === v)?.label || v)
    .join(' + ')
  return [...BASE_STATUSES, { value: current, label }]
})

const filtered = computed(() => {
  const f = filters.value
  return submissionStore.orgSubmissions.filter((s) => {
    if (f.status && !f.status.split(',').includes(s.status)) return false
    if (f.type && s.type !== f.type) return false
    if (f.priority && s.priority !== f.priority) return false
    if (f.assignee === 'unassigned' && s.assigned_to) return false
    if (f.assignee && f.assignee !== 'unassigned' && String(s.assigned_to?.id) !== f.assignee) return false
    if (f.branch && String(s.branch || '') !== f.branch) return false
    if (f.category && s.category !== f.category) return false
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
  filters.value = { status: '', type: '', priority: '', search: '', assignee: '', branch: '', category: '', dateFrom: '', dateTo: '' }
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
  await loadQueue()
}

function exportCSV() {
  const selected = filtered.value.filter((s) => selectedIds.value.has(s.id))
  const rows = [
    ['Reference', 'Title', 'Type', 'Priority', 'Status', 'Branch', 'Submitter', 'Assigned To', 'Date'],
    ...selected.map((s) => [
      s.reference_number,
      s.title,
      s.type,
      s.priority,
      s.status,
      s.branch_name || '',
      s.is_anonymous ? 'Anonymous' : (s.submitter_name || ''),
      s.assigned_to?.user_name || '',
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
  await loadQueue()

  // ?ref=GUN-... deep-links straight into a submission's detail panel
  const ref = route.query.ref
  if (typeof ref === 'string' && ref) {
    const match = submissionStore.orgSubmissions.find((s) => s.reference_number === ref)
    if (match) openDetail(match)
    else {
      // Older than the loaded page — fetch it directly.
      try {
        openDetail(await submissionStore.refreshSubmission(ref))
      } catch {
        uiStore.showInfo(`Submission ${ref} was not found.`)
      }
    }
    router.replace({ query: { ...route.query, ref: undefined } })
  }
})

// `orgStore.currentOrg` can still be resolving (OrgLayout fetches it
// asynchronously) when this page mounts on a hard refresh, so a watcher is
// used instead of a one-shot check in onMounted — see OrgBranchesPage.vue
// for the full rationale.
watch(
  () => orgStore.currentOrg?.slug,
  (slug) => {
    if (slug) {
      orgStore.fetchStaff(slug)
      orgStore.fetchBranches(slug)
    }
  },
  { immediate: true }
)
</script>

<template>
  <div class="p-6 space-y-5">
    <div class="flex items-center justify-between gap-3 flex-wrap">
      <h1 class="text-xl font-extrabold text-secondary dark:text-white">Submissions</h1>
      <button @click="exportAll" :disabled="exporting" class="btn-secondary !py-2 !px-4 text-sm">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
        </svg>
        {{ exporting ? 'Preparing…' : 'Export CSV' }}
      </button>
    </div>

    <div class="flex gap-1.5 overflow-x-auto pb-1" role="tablist" aria-label="Work queues">
      <button v-for="q in QUEUES" :key="q.key" role="tab" :aria-selected="queue === q.key" @click="queue = q.key"
        :class="['shrink-0 px-3.5 py-2 rounded-xl text-sm font-semibold transition-colors',
          queue === q.key ? 'bg-secondary text-white shadow-sm' : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:border-gray-300']">
        {{ q.label }}
      </button>
    </div>

    <FilterBar
      v-model="filters"
      :statuses="STATUSES"
      :show-assignee="true"
      :show-date-range="true"
      :staff-list="orgStore.staff"
      :show-branch="orgStore.branches.length > 0"
      :branch-list="orgStore.branches"
      :count="filtered.length"
      @clear="clearFilters" />

    <p v-if="!submissionStore.loading && submissionStore.orgSubmissionsCount > submissionStore.orgSubmissions.length"
      class="text-xs text-gray-500 dark:text-gray-400">
      Showing the {{ submissionStore.orgSubmissions.length }} most recent of {{ submissionStore.orgSubmissionsCount }} in this queue —
      use a narrower queue, or Export CSV for all of them.
    </p>

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
              <th class="px-4 py-3 text-left">Branch</th>
              <th class="px-4 py-3 text-left">Assigned</th>
              <th class="px-4 py-3 text-left">Date</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 dark:divide-gray-700/50">
            <tr v-if="!filtered.length">
              <td colspan="9" class="px-4 py-12 text-center text-gray-400 dark:text-gray-500 text-sm">
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
                <p class="text-xs text-gray-400 dark:text-gray-500 mt-0.5 flex items-center gap-1.5 flex-wrap">
                  {{ sub.is_anonymous ? 'Anonymous' : (sub.submitter_name || '—') }}
                  <span v-if="sub.is_overdue" class="px-1.5 py-px rounded-full text-[10px] font-bold bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-300">Overdue</span>
                  <span v-if="sub.awaiting_reply" class="px-1.5 py-px rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-200">Citizen waiting</span>
                  <span v-if="sub.satisfaction_score" class="text-[10px] font-bold text-amber-500">★ {{ sub.satisfaction_score }}</span>
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
                {{ sub.branch_name || '—' }}
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-xs text-gray-500 dark:text-gray-400">
                {{ sub.assigned_to?.user_name || '—' }}
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
