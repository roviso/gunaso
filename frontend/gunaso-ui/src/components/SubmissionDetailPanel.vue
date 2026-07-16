<script setup>
import { ref, computed, watch } from 'vue'
import { useSubmissionStore } from '@/stores/submission'
import { useOrganizationStore } from '@/stores/organization'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import { apiErrorMessage } from '@/api/index'
import StatusBadge from '@/components/StatusBadge.vue'
import PriorityBadge from '@/components/PriorityBadge.vue'
import SubmissionTimeline from '@/components/SubmissionTimeline.vue'

const props = defineProps({
  submission: { type: Object, default: null },
})
const emit = defineEmits(['close', 'updated'])

const submissionStore = useSubmissionStore()
const orgStore = useOrganizationStore()
const authStore = useAuthStore()
const uiStore = useUIStore()

// Status transitions mutate a submission (see apps/submissions/services.py::
// transition_status, gated server-side by 'manage_submissions'). A staff
// member who can only view submissions must not see an actionable control
// here — org admins implicitly hold every privilege (authStore.hasPrivilege).
const canManageSubmissions = computed(() => authStore.hasPrivilege('manage_submissions'))

const statusUpdate = ref({ status: '', note: '' })
const noteText = ref('')
const assigneeId = ref('')
const updatingStatus = ref(false)
const addingNote = ref(false)
const assigning = ref(false)
const togglingVisibility = ref(false)

const VALID_TRANSITIONS = {
  submitted:    ['acknowledged', 'in_review', 'rejected', 'escalated'],
  acknowledged: ['in_review', 'rejected', 'escalated'],
  in_review:    ['resolved', 'rejected', 'escalated'],
  escalated:    ['in_review', 'resolved', 'rejected'],
  resolved:     ['closed'],
  rejected:     ['closed'],
  closed:       [],
}

const STATUS_LABELS = {
  submitted: 'Submitted', acknowledged: 'Acknowledged', in_review: 'In Review',
  resolved: 'Resolved', rejected: 'Rejected', escalated: 'Escalated', closed: 'Closed',
}

const allowedNextStatuses = computed(() => {
  const current = props.submission?.status
  return (VALID_TRANSITIONS[current] || []).map((s) => ({ value: s, label: STATUS_LABELS[s] }))
})

watch(() => props.submission, (sub) => {
  if (sub) {
    statusUpdate.value = { status: '', note: '' }
    noteText.value = ''
    assigneeId.value = sub.assigned_to_id ? String(sub.assigned_to_id) : ''
  }
})

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

async function submitStatusUpdate() {
  if (!statusUpdate.value.status || updatingStatus.value) return
  updatingStatus.value = true
  try {
    const updated = await submissionStore.updateStatus(
      props.submission.reference_number,
      statusUpdate.value
    )
    uiStore.showSuccess('Status updated.')
    statusUpdate.value = { status: '', note: '' }
    emit('updated', updated)
  } catch (err) {
    uiStore.showError(apiErrorMessage(err, 'Failed to update status.'))
  } finally {
    updatingStatus.value = false
  }
}

async function submitNote() {
  if (!noteText.value.trim() || addingNote.value) return
  addingNote.value = true
  try {
    await submissionStore.addNote(props.submission.reference_number, noteText.value.trim())
    uiStore.showSuccess('Note added.')
    noteText.value = ''
    emit('updated')
  } catch (err) {
    uiStore.showError(apiErrorMessage(err, 'Failed to add note.'))
  } finally {
    addingNote.value = false
  }
}

async function submitAssign() {
  if (assigning.value) return
  assigning.value = true
  try {
    await submissionStore.assignSubmission(
      props.submission.reference_number,
      assigneeId.value || null
    )
    uiStore.showSuccess('Assigned successfully.')
    emit('updated')
  } catch (err) {
    uiStore.showError(apiErrorMessage(err, 'Failed to assign.'))
  } finally {
    assigning.value = false
  }
}

async function togglePublic() {
  if (togglingVisibility.value) return
  togglingVisibility.value = true
  try {
    const updated = await submissionStore.setVisibility(props.submission.reference_number, !props.submission.is_public)
    uiStore.showSuccess(updated.is_public ? 'Added to the public showcase.' : 'Removed from the public showcase.')
    emit('updated', updated)
  } catch (err) {
    uiStore.showError(apiErrorMessage(err, 'Failed to update public visibility.'))
  } finally {
    togglingVisibility.value = false
  }
}

const typeIcon = { complaint: '⚠️', feedback: '💬', suggestion: '💡' }
</script>

<template>
  <Teleport to="body">
    <Transition name="panel">
      <div v-if="submission" class="fixed inset-0 z-40 flex justify-end">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/30 backdrop-blur-sm" @click="$emit('close')" />

        <!-- Slide-in panel -->
        <div class="relative z-50 w-full max-w-lg bg-white dark:bg-gray-800 shadow-2xl flex flex-col h-full overflow-hidden border-l border-gray-200 dark:border-gray-700">
          <!-- Header -->
          <div class="flex items-start justify-between p-5 border-b border-gray-100 dark:border-gray-700 shrink-0">
            <div class="min-w-0 flex-1 pr-3">
              <div class="flex flex-wrap items-center gap-2 mb-2">
                <span class="text-lg leading-none">{{ typeIcon[submission.type] || '📋' }}</span>
                <span class="font-mono text-xs bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 px-2 py-0.5 rounded">
                  {{ submission.reference_number }}
                </span>
                <StatusBadge :status="submission.status" />
                <PriorityBadge :priority="submission.priority" />
              </div>
              <h2 class="font-bold text-gray-900 dark:text-white leading-tight">{{ submission.title }}</h2>
              <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                {{ submission.is_anonymous ? 'Anonymous' : (submission.submitter_name || '—') }}
                · {{ formatDate(submission.created_at) }}
              </p>
            </div>
            <button @click="$emit('close')"
              class="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors shrink-0">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <!-- Scrollable body -->
          <div class="flex-1 overflow-y-auto p-5 space-y-6">
            <!-- Description -->
            <div>
              <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2">Description</h3>
              <p class="text-sm text-gray-700 dark:text-gray-300 leading-relaxed bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4">
                {{ submission.description }}
              </p>
            </div>

            <!-- Contact -->
            <div v-if="!submission.is_anonymous && (submission.submitter_email || submission.submitter_phone)">
              <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2">Contact</h3>
              <div class="text-sm space-y-1 text-gray-700 dark:text-gray-300">
                <p v-if="submission.submitter_email">{{ submission.submitter_email }}</p>
                <p v-if="submission.submitter_phone">{{ submission.submitter_phone }}</p>
              </div>
            </div>

            <!-- Attachment -->
            <div v-if="submission.attachment">
              <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2">Attachment</h3>
              <a :href="submission.attachment" target="_blank" rel="noopener"
                class="inline-flex items-center gap-2 text-sm text-primary hover:underline">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"/>
                </svg>
                View attachment
              </a>
            </div>

            <!-- Update status -->
            <div>
              <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-3">Update Status</h3>
              <div v-if="!canManageSubmissions" title="You don't have permission to change submission status"
                class="text-sm text-gray-400 dark:text-gray-500 italic cursor-not-allowed">
                You don't have permission to change this submission's status.
              </div>
              <div v-else-if="allowedNextStatuses.length" class="space-y-3">
                <select v-model="statusUpdate.status" class="input-base">
                  <option value="">Select new status…</option>
                  <option v-for="s in allowedNextStatuses" :key="s.value" :value="s.value">{{ s.label }}</option>
                </select>
                <textarea v-model="statusUpdate.note" rows="2"
                  placeholder="Optional note to citizen…"
                  class="input-base resize-none" maxlength="500" />
                <button @click="submitStatusUpdate"
                  :disabled="!statusUpdate.status || updatingStatus"
                  class="btn-primary w-full py-2.5 text-sm disabled:opacity-50">
                  <svg v-if="updatingStatus" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  {{ updatingStatus ? 'Saving…' : 'Update Status' }}
                </button>
              </div>
              <p v-else class="text-sm text-gray-400 dark:text-gray-500 italic">No further transitions available.</p>
            </div>

            <!-- Assign to staff -->
            <div v-if="orgStore.staff.length">
              <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-3">Assign To</h3>
              <div class="flex gap-2">
                <select v-model="assigneeId" class="input-base flex-1">
                  <option value="">Unassigned</option>
                  <option v-for="s in orgStore.staff" :key="s.id" :value="String(s.id)">
                    {{ s.name || s.user?.name || s.email }}
                  </option>
                </select>
                <button @click="submitAssign" :disabled="assigning"
                  class="btn-secondary px-4 py-2.5 text-sm whitespace-nowrap disabled:opacity-50">
                  {{ assigning ? '…' : 'Assign' }}
                </button>
              </div>
            </div>

            <!-- Add internal note -->
            <div>
              <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-3">Add Internal Note</h3>
              <div class="space-y-2">
                <textarea v-model="noteText" rows="2"
                  placeholder="Internal note (not visible to citizen)…"
                  class="input-base resize-none" maxlength="1000" />
                <button @click="submitNote" :disabled="!noteText.trim() || addingNote"
                  class="btn-secondary w-full py-2 text-sm disabled:opacity-50">
                  {{ addingNote ? 'Adding…' : 'Add Note' }}
                </button>
              </div>
            </div>

            <!-- Public showcase -->
            <div v-if="canManageSubmissions">
              <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-3">Public Showcase</h3>
              <div class="flex items-center justify-between gap-3 bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4">
                <div class="min-w-0">
                  <p class="text-sm font-medium text-gray-700 dark:text-gray-200">
                    {{ submission.is_public ? 'Visible on the public profile' : 'Not shown on the public profile' }}
                  </p>
                  <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    Shows title, status, and timeline{{ submission.is_anonymous ? '' : ' with the submitter\'s name' }} on your organization's public page.
                  </p>
                </div>
                <button @click="togglePublic" :disabled="togglingVisibility"
                  role="switch" :aria-checked="submission.is_public"
                  :class="['relative shrink-0 w-11 h-6 rounded-full transition-colors disabled:opacity-50',
                    submission.is_public ? 'bg-primary' : 'bg-gray-300 dark:bg-gray-600']">
                  <span :class="['absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform',
                    submission.is_public ? 'translate-x-5' : 'translate-x-0']" />
                </button>
              </div>
            </div>

            <!-- Timeline -->
            <div>
              <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-3">Status History</h3>
              <SubmissionTimeline :timeline="submission.timeline || []" />
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.panel-enter-active, .panel-leave-active { transition: transform 0.25s ease, opacity 0.25s ease; }
.panel-enter-from, .panel-leave-to { transform: translateX(100%); opacity: 0.5; }
</style>
