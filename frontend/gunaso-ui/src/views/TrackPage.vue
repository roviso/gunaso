<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useSubmissionStore } from '@/stores/submission'
import StatusBadge from '@/components/StatusBadge.vue'
import PriorityBadge from '@/components/PriorityBadge.vue'
import SubmissionTimeline from '@/components/SubmissionTimeline.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const submissionStore = useSubmissionStore()

const reference = ref('')
const searched = ref(false)

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
}

async function handleTrack() {
  if (!reference.value.trim()) return
  searched.value = false
  try {
    await submissionStore.fetchByReference(reference.value.trim().toUpperCase())
    searched.value = true
  } catch {
    searched.value = true
  }
}

onMounted(() => {
  if (route.query.ref) {
    reference.value = String(route.query.ref)
    handleTrack()
  }
})

const typeLabel = { complaint: 'Complaint', feedback: 'Feedback', suggestion: 'Suggestion' }
const typeColor = { complaint: 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300', feedback: 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300', suggestion: 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300' }
</script>

<template>
  <div class="bg-app-bg dark:bg-gray-900 min-h-[calc(100vh-4rem)]">
    <!-- Hero -->
    <div class="bg-gradient-to-br from-secondary to-[#0f1f38] text-white py-14">
      <div class="page-container text-center">
        <div class="w-14 h-14 bg-white/10 rounded-2xl flex items-center justify-center mx-auto mb-5">
          <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>
          </svg>
        </div>
        <h1 class="text-3xl sm:text-4xl font-extrabold mb-3">Track Your Complaint</h1>
        <p class="text-blue-200 text-base max-w-lg mx-auto mb-8">
          Enter your reference number to check the current status and view updates from the organization.
        </p>

        <!-- Search box -->
        <div class="max-w-lg mx-auto flex gap-2">
          <input v-model="reference" @keydown.enter="handleTrack"
            type="text" placeholder="e.g. GUN-2024-00001"
            class="flex-1 px-5 py-3.5 rounded-xl border border-white/20 bg-white/10 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/30 focus:bg-white/15 text-sm font-mono uppercase tracking-wider backdrop-blur-sm transition-all" />
          <button @click="handleTrack" :disabled="submissionStore.loading || !reference.trim()"
            class="px-6 py-3.5 bg-primary hover:bg-primary-600 text-white font-semibold rounded-xl transition-colors disabled:opacity-50 whitespace-nowrap">
            Track
          </button>
        </div>
        <p class="text-blue-300 text-xs mt-3">Format: GUN-YYYY-NNNNN (case insensitive)</p>
      </div>
    </div>

    <!-- Results -->
    <div class="page-container py-10">
      <LoadingSpinner v-if="submissionStore.loading" label="Fetching submission..." />

      <!-- Error state -->
      <div v-else-if="searched && submissionStore.error" class="max-w-lg mx-auto text-center py-12">
        <div class="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-5">
          <svg class="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        </div>
        <h3 class="text-lg font-bold text-gray-900 dark:text-white mb-2">Submission Not Found</h3>
        <p class="text-gray-500 dark:text-gray-400 text-sm mb-6">{{ submissionStore.error }}</p>
        <div class="flex flex-col sm:flex-row gap-3 justify-center">
          <RouterLink to="/submit" class="btn-primary">Submit a New Complaint</RouterLink>
          <button @click="reference = ''; submissionStore.error = null; searched = false" class="btn-secondary">Clear & Try Again</button>
        </div>
      </div>

      <!-- Submission found -->
      <div v-else-if="searched && submissionStore.currentSubmission" class="max-w-2xl mx-auto space-y-5">
        <!-- Header card -->
        <div class="card p-6">
          <div class="flex items-start justify-between gap-4 flex-wrap mb-4">
            <div>
              <div class="flex items-center gap-2 mb-1">
                <span class="text-xs font-mono text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-gray-700 px-2.5 py-1 rounded-lg">
                  {{ submissionStore.currentSubmission.reference_number }}
                </span>
                <span v-if="submissionStore.currentSubmission.type" :class="['text-xs font-semibold px-2.5 py-1 rounded-lg', typeColor[submissionStore.currentSubmission.type]]">
                  {{ typeLabel[submissionStore.currentSubmission.type] }}
                </span>
              </div>
              <h2 class="text-xl font-bold text-gray-900 dark:text-white mt-2">
                {{ submissionStore.currentSubmission.title }}
              </h2>
              <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Submitted to <span class="font-medium text-accent">{{ submissionStore.currentSubmission.organization_name }}</span>
                · {{ formatDate(submissionStore.currentSubmission.created_at) }}
              </p>
            </div>
            <div class="flex flex-col items-end gap-2">
              <StatusBadge :status="submissionStore.currentSubmission.status" />
              <PriorityBadge :priority="submissionStore.currentSubmission.priority" />
            </div>
          </div>

          <div v-if="submissionStore.currentSubmission.description"
            class="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4 text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
            {{ submissionStore.currentSubmission.description }}
          </div>
        </div>

        <!-- Timeline -->
        <div class="card p-6">
          <h3 class="font-bold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
            <svg class="w-5 h-5 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            Status History
          </h3>
          <SubmissionTimeline :timeline="submissionStore.currentSubmission.timeline || []" />
        </div>

        <!-- Actions -->
        <div class="flex gap-3 justify-center flex-wrap">
          <RouterLink to="/submit" class="btn-secondary text-sm">Submit Another</RouterLink>
          <button @click="reference = ''; submissionStore.currentSubmission = null; searched = false"
            class="btn-ghost text-sm">Track Different Reference</button>
        </div>
      </div>

      <!-- Empty state (before search) -->
      <div v-else-if="!submissionStore.loading" class="text-center py-16">
        <svg class="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
        <p class="text-gray-500 dark:text-gray-400 text-sm">Enter your reference number above to track your complaint.</p>
        <p class="text-gray-400 dark:text-gray-500 text-xs mt-2">
          You can find it in the confirmation email or on your submission receipt.
        </p>
      </div>
    </div>
  </div>
</template>
