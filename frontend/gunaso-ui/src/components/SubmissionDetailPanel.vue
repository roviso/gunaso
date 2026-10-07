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
// 'reply' is shown to (and emailed to) the citizen; 'internal' never leaves the org.
const noteMode = ref('reply')
const assigneeId = ref('')
const updatingStatus = ref(false)
const addingNote = ref(false)
const assigning = ref(false)
const togglingVisibility = ref(false)

const categoryInput = ref('')
const savingCategory = ref(false)
const classifying = ref(false)
const classifyError = ref('')
const generatingSujhav = ref(false)
const sujhavError = ref('')

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
    noteMode.value = 'reply'
    assigneeId.value = sub.assigned_to?.id ? String(sub.assigned_to.id) : ''
    categoryInput.value = sub.category || ''
    classifyError.value = ''
    sujhavError.value = ''
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
  const internal = noteMode.value === 'internal'
  try {
    await submissionStore.addNote(props.submission.reference_number, noteText.value.trim(), internal)
    uiStore.showSuccess(internal ? 'Internal note saved.' : 'Reply sent to the citizen.')
    noteText.value = ''
    emit('updated', submissionStore.orgSubmissions.find((s) => s.reference_number === props.submission.reference_number))
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

async function submitCategory() {
  if (!categoryInput.value.trim() || savingCategory.value) return
  savingCategory.value = true
  try {
    const updated = await submissionStore.updateCategory(props.submission.reference_number, categoryInput.value.trim())
    uiStore.showSuccess('Category updated.')
    emit('updated', updated)
  } catch (err) {
    uiStore.showError(apiErrorMessage(err, 'Failed to update category.'))
  } finally {
    savingCategory.value = false
  }
}

async function runAIClassify() {
  if (classifying.value) return
  classifying.value = true
  classifyError.value = ''
  try {
    const result = await submissionStore.aiClassify(props.submission.reference_number)
    categoryInput.value = result.submission.category || categoryInput.value
    uiStore.showSuccess(
      result.applied ? 'AI classified and applied a category.' : 'AI suggestion ready — review and apply below.'
    )
    emit('updated', result.submission)
  } catch (err) {
    classifyError.value = apiErrorMessage(err, 'AI classification is unavailable right now.')
  } finally {
    classifying.value = false
  }
}

async function applyAISuggestion() {
  if (!props.submission?.ai_insight?.suggested_category) return
  categoryInput.value = props.submission.ai_insight.suggested_category
  await submitCategory()
}

async function runGenerateSujhav() {
  if (generatingSujhav.value) return
  generatingSujhav.value = true
  sujhavError.value = ''
  try {
    const updated = await submissionStore.generateSujhav(props.submission.reference_number)
    uiStore.showSuccess('AI सुझाव generated.')
    emit('updated', updated)
  } catch (err) {
    sujhavError.value = apiErrorMessage(err, 'AI suggestion is unavailable right now.')
  } finally {
    generatingSujhav.value = false
  }
}

const sentimentMeta = {
  positive: { label: 'Positive', class: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' },
  neutral: { label: 'Neutral', class: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300' },
  negative: { label: 'Negative', class: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' },
}

const typeIcon = { complaint: '⚠️', feedback: '💬', suggestion: '💡' }

// Whether a public reply will actually reach the citizen's inbox — anonymous
// submitters are never emailed, and guests may not have left an address.
const citizenReachable = computed(() =>
  !props.submission?.is_anonymous && !!props.submission?.submitter_email
)
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
                <span v-if="submission.is_overdue"
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300 border border-red-200 dark:border-red-800">
                  ⏰ Overdue
                </span>
                <span v-if="submission.awaiting_reply"
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-secondary/10 text-secondary dark:bg-blue-900/30 dark:text-blue-200">
                  💬 Citizen waiting
                </span>
              </div>
              <h2 class="font-bold text-gray-900 dark:text-white leading-tight">{{ submission.title }}</h2>
              <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                {{ submission.is_anonymous ? 'Anonymous' : (submission.submitter_name || '—') }}
                · {{ formatDate(submission.created_at) }}
                <span v-if="submission.branch_name"> · {{ submission.branch_name }} branch</span>
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

            <!-- Citizen's verdict -->
            <div v-if="submission.satisfaction_score" class="flex items-start gap-3 p-4 rounded-xl bg-amber-50 dark:bg-amber-900/15 border border-amber-100 dark:border-amber-800/60">
              <div class="text-amber-500 text-lg leading-none tracking-tight" :aria-label="`${submission.satisfaction_score} out of 5`">
                {{ '★'.repeat(submission.satisfaction_score) }}<span class="text-amber-200 dark:text-amber-800">{{ '★'.repeat(5 - submission.satisfaction_score) }}</span>
              </div>
              <div class="min-w-0">
                <p class="text-xs font-semibold text-amber-800 dark:text-amber-300 uppercase tracking-wide">Citizen's rating of the outcome</p>
                <p v-if="submission.satisfaction_comment" class="text-sm text-gray-700 dark:text-gray-200 mt-1">“{{ submission.satisfaction_comment }}”</p>
              </div>
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

            <!-- Category -->
            <div v-if="canManageSubmissions">
              <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2">Category</h3>
              <div class="flex gap-2">
                <input v-model="categoryInput" type="text" placeholder="e.g. Billing Dispute"
                  class="input-base flex-1" maxlength="100" />
                <button @click="submitCategory" :disabled="!categoryInput.trim() || savingCategory"
                  class="btn-secondary !px-4 text-sm disabled:opacity-50 shrink-0">
                  {{ savingCategory ? 'Saving…' : 'Save' }}
                </button>
              </div>

              <!-- AI suggestion -->
              <div v-if="submission.ai_insight" class="mt-2.5 flex items-start gap-2 p-2.5 rounded-lg bg-violet-50 dark:bg-violet-900/15 border border-violet-100 dark:border-violet-800">
                <span class="text-sm shrink-0">🤖</span>
                <div class="flex-1 min-w-0 text-xs">
                  <p class="text-violet-700 dark:text-violet-300">
                    AI suggests <span class="font-semibold">{{ submission.ai_insight.suggested_category }}</span>
                    ({{ Math.round(submission.ai_insight.confidence * 100) }}% confident)
                    <span :class="['ml-1 px-1.5 py-0.5 rounded-full font-semibold', sentimentMeta[submission.ai_insight.sentiment]?.class]">
                      {{ sentimentMeta[submission.ai_insight.sentiment]?.label }}
                    </span>
                  </p>
                  <p v-if="submission.ai_insight.applied" class="text-violet-500 dark:text-violet-400 mt-0.5">Already applied.</p>
                  <button v-else @click="applyAISuggestion" class="text-primary hover:underline font-medium mt-0.5">
                    Apply this category
                  </button>
                </div>
              </div>

              <button @click="runAIClassify" :disabled="classifying"
                class="mt-2.5 flex items-center gap-1.5 text-xs font-semibold text-violet-600 dark:text-violet-400 hover:underline disabled:opacity-50">
                <svg v-if="classifying" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                {{ classifying ? 'Classifying…' : (submission.ai_insight ? 'Re-run AI Classification' : '🤖 AI Classify') }}
              </button>
              <p v-if="classifyError" class="field-error mt-1">{{ classifyError }}</p>
            </div>
            <div v-else-if="submission.category">
              <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2">Category</h3>
              <p class="text-sm text-gray-700 dark:text-gray-300">{{ submission.category }}</p>
            </div>

            <!-- AI सुझाव (suggestion) -->
            <div v-if="canManageSubmissions">
              <div class="flex items-center justify-between mb-2">
                <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">AI सुझाव (Suggestion)</h3>
                <button @click="runGenerateSujhav" :disabled="generatingSujhav"
                  class="flex items-center gap-1.5 text-xs font-semibold text-violet-600 dark:text-violet-400 hover:underline disabled:opacity-50">
                  <svg v-if="generatingSujhav" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  {{ generatingSujhav ? 'Generating…' : (submission.ai_suggestion ? 'Regenerate' : '🤖 Get Suggestion') }}
                </button>
              </div>
              <div v-if="submission.ai_suggestion" class="space-y-2.5 p-3 rounded-xl bg-violet-50 dark:bg-violet-900/15 border border-violet-100 dark:border-violet-800 text-sm text-violet-900 dark:text-violet-200">
                <p>{{ submission.ai_suggestion.suggestion_nepali }}</p>
                <p class="pt-2.5 border-t border-violet-200/60 dark:border-violet-800/60 text-violet-700 dark:text-violet-300">
                  {{ submission.ai_suggestion.suggestion_english }}
                </p>
              </div>
              <p v-else class="text-xs text-gray-400 dark:text-gray-500 italic">No AI suggestion yet.</p>
              <p v-if="sujhavError" class="field-error mt-1">{{ sujhavError }}</p>
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
                  placeholder="Optional message to the citizen (shown on their timeline and emailed)…"
                  class="input-base resize-none" maxlength="2000" />
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

            <!-- Conversation composer: public reply vs internal note -->
            <div v-if="canManageSubmissions">
              <div class="flex items-center gap-1 p-1 mb-3 rounded-xl bg-gray-100 dark:bg-gray-700/60 w-fit" role="tablist">
                <button v-for="m in [{ v: 'reply', l: 'Reply to citizen' }, { v: 'internal', l: '🔒 Internal note' }]" :key="m.v"
                  role="tab" :aria-selected="noteMode === m.v" @click="noteMode = m.v"
                  :class="['px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors',
                    noteMode === m.v ? 'bg-white dark:bg-gray-800 text-secondary dark:text-white shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700']">
                  {{ m.l }}
                </button>
              </div>
              <div class="space-y-2">
                <textarea v-model="noteText" rows="3"
                  :placeholder="noteMode === 'reply' ? 'Write a reply the citizen will see on their timeline…' : 'Only your team will see this note…'"
                  :class="['input-base resize-none', noteMode === 'internal' ? 'bg-amber-50/60 dark:bg-amber-900/10 border-amber-200 dark:border-amber-800' : '']"
                  maxlength="4000" />
                <p class="text-[11px] text-gray-400 dark:text-gray-500">
                  <template v-if="noteMode === 'internal'">Never shown to the citizen, never emailed, never on the public page.</template>
                  <template v-else-if="citizenReachable">Appears on the citizen's timeline and is emailed to them.</template>
                  <template v-else>Appears on the citizen's tracking page. {{ submission.is_anonymous ? 'Anonymous submitters are never emailed.' : 'They left no email, so they won\'t be notified.' }}</template>
                </p>
                <button @click="submitNote" :disabled="!noteText.trim() || addingNote"
                  :class="[noteMode === 'reply' ? 'btn-primary' : 'btn-secondary', 'w-full !py-2.5 text-sm disabled:opacity-50']">
                  {{ addingNote ? 'Saving…' : noteMode === 'reply' ? 'Send reply' : 'Save internal note' }}
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
              <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-3">Case history</h3>
              <SubmissionTimeline :timeline="submission.timeline || []" audience="org" />
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
