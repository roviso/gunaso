<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSubmissionStore } from '@/stores/submission'
import { useSavedSubmissionsStore } from '@/stores/savedSubmissions'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import { apiErrorMessage } from '@/api/index'
import StatusBadge from '@/components/StatusBadge.vue'
import StatusProgress from '@/components/StatusProgress.vue'
import SubmissionTimeline from '@/components/SubmissionTimeline.vue'

const route = useRoute()
const router = useRouter()
const submissionStore = useSubmissionStore()
const saved = useSavedSubmissionsStore()
const authStore = useAuthStore()
const uiStore = useUIStore()

const reference = ref('')
const searched = ref(false)
// The private follow-up key: from the URL fragment (#key=… in the emailed /
// receipt link), else remembered on this device. Never put in a query string.
const followupKey = ref('')

const replyText = ref('')
const sendingReply = ref(false)
const replyError = ref('')

const rating = ref(0)
const hoverRating = ref(0)
const ratingComment = ref('')
const sendingRating = ref(false)
const ratingError = ref('')
const editingRating = ref(false)

const sub = computed(() => submissionStore.currentSubmission)
const REF_PATTERN = /^GUN-\d{4}-[A-Z0-9]{5,8}$/

function normalize(value) {
  return String(value || '').trim().toUpperCase()
}

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
}

function readKeyFromHash() {
  const match = /(?:^#|&)key=([^&]+)/.exec(window.location.hash || '')
  return match ? decodeURIComponent(match[1]) : ''
}

async function load(ref_) {
  const refValue = normalize(ref_)
  if (!refValue) return
  reference.value = refValue
  searched.value = false
  const key = followupKey.value || saved.keyFor(refValue)
  try {
    await submissionStore.fetchByReference(refValue, key)
    followupKey.value = key
    const data = submissionStore.currentSubmission
    if (data?.can_follow_up) {
      saved.save({ ref: refValue, key, organization: data.organization_name, title: data.title })
    }
    rating.value = data?.satisfaction_score || 0
    ratingComment.value = data?.satisfaction_comment || ''
    editingRating.value = false
  } catch {
    /* error state is rendered from submissionStore.error */
  } finally {
    searched.value = true
  }
}

function handleTrack() {
  const refValue = normalize(reference.value)
  if (!refValue) return
  followupKey.value = ''
  if (refValue === normalize(route.params.ref)) load(refValue)
  else router.push({ name: 'Track', params: { ref: refValue } })
}

function printPage() {
  window.print()
}

function openSaved(entry) {
  followupKey.value = entry.key || ''
  router.push({ name: 'Track', params: { ref: entry.ref } })
}

watch(() => route.params.ref, (value) => {
  if (value) load(value)
  else {
    submissionStore.currentSubmission = null
    searched.value = false
  }
})

onMounted(() => {
  const hashKey = readKeyFromHash()
  if (hashKey) {
    followupKey.value = hashKey
    // Keep the credential out of the visible address bar / screenshots; it's
    // remembered on this device and still in the confirmation email.
    history.replaceState(history.state, '', window.location.pathname + window.location.search)
  }
  const initial = route.params.ref || route.query.ref
  if (initial) {
    if (!route.params.ref) router.replace({ name: 'Track', params: { ref: normalize(initial) } })
    else load(initial)
  }
})

const typeLabel = { complaint: 'Complaint', feedback: 'Feedback', suggestion: 'Suggestion' }
const typeIcon = { complaint: '⚠️', feedback: '💬', suggestion: '💡' }

const nextStep = computed(() => {
  const s = sub.value
  if (!s) return null
  const org = s.organization_name
  const hours = s.response_target_hours
  return {
    submitted: {
      tone: s.is_overdue ? 'warn' : 'info',
      title: s.is_overdue ? 'Waiting longer than it should' : 'Waiting for the organization',
      body: s.is_overdue
        ? `${org} hasn't acknowledged this within the ${hours}-hour response target. The delay is visible on their dashboard as overdue.`
        : `${org} has been notified. Organizations on Gunaso are expected to acknowledge within ${hours} hours.`,
    },
    acknowledged: { tone: 'info', title: 'Received and acknowledged', body: `${org} has seen your gunaso and will start working on it.` },
    in_review: { tone: 'info', title: 'Being worked on', body: `Someone at ${org} is actively looking into it. Replies will appear below.` },
    escalated: { tone: 'warn', title: 'Escalated', body: `Your gunaso has been escalated to a more senior team at ${org}.` },
    resolved: { tone: 'good', title: 'Marked as resolved', body: 'Was it actually fixed? Your rating keeps organizations honest.' },
    rejected: { tone: 'bad', title: 'No action will be taken', body: `${org} decided not to act on this gunaso. Their note in the history explains why.` },
    closed: { tone: 'neutral', title: 'Case closed', body: 'If the problem comes back, file a new gunaso any time.' },
  }[s.status]
})

const toneClass = {
  info: 'bg-blue-50 border-blue-100 text-blue-900 dark:bg-blue-900/20 dark:border-blue-800 dark:text-blue-100',
  warn: 'bg-amber-50 border-amber-200 text-amber-900 dark:bg-amber-900/20 dark:border-amber-800 dark:text-amber-100',
  good: 'bg-green-50 border-green-200 text-green-900 dark:bg-green-900/20 dark:border-green-800 dark:text-green-100',
  bad: 'bg-red-50 border-red-200 text-red-900 dark:bg-red-900/20 dark:border-red-800 dark:text-red-100',
  neutral: 'bg-gray-50 border-gray-200 text-gray-800 dark:bg-gray-700/40 dark:border-gray-600 dark:text-gray-100',
}

const canRate = computed(() => ['resolved', 'rejected', 'closed'].includes(sub.value?.status))
const canReply = computed(() => sub.value?.can_follow_up && sub.value?.status !== 'closed')

async function sendReply() {
  if (!replyText.value.trim() || sendingReply.value) return
  sendingReply.value = true
  replyError.value = ''
  try {
    await submissionStore.replyAsCitizen(sub.value.reference_number, replyText.value.trim(), followupKey.value)
    replyText.value = ''
    uiStore.showSuccess('Your follow-up was added to the case.')
  } catch (err) {
    replyError.value = apiErrorMessage(err, 'Could not send your follow-up.')
  } finally {
    sendingReply.value = false
  }
}

async function sendRating() {
  if (!rating.value || sendingRating.value) return
  sendingRating.value = true
  ratingError.value = ''
  try {
    await submissionStore.rateOutcome(sub.value.reference_number, rating.value, ratingComment.value.trim(), followupKey.value)
    editingRating.value = false
    uiStore.showSuccess('Thank you — your rating was recorded.')
  } catch (err) {
    ratingError.value = apiErrorMessage(err, 'Could not save your rating.')
  } finally {
    sendingRating.value = false
  }
}

async function copyLink(withKey = false) {
  const base = `${window.location.origin}/track/${sub.value.reference_number}`
  const link = withKey && followupKey.value ? `${base}#key=${encodeURIComponent(followupKey.value)}` : base
  try {
    await navigator.clipboard.writeText(link)
    uiStore.showSuccess(withKey ? 'Private link copied — keep it to yourself.' : 'Public status link copied.')
  } catch {
    uiStore.showError('Could not copy — your browser blocked clipboard access.')
  }
}

const ratingLabels = ['', 'Very poor', 'Poor', 'Okay', 'Good', 'Excellent']
</script>

<template>
  <div class="bg-app-bg dark:bg-gray-900 min-h-[calc(100vh-4rem)]">
    <!-- Hero / search -->
    <div class="relative bg-gradient-to-br from-secondary via-[#16294a] to-secondary-900 text-white overflow-hidden">
      <div class="pointer-events-none absolute inset-0 opacity-[0.05]"
        style="background-image: radial-gradient(currentColor 1px, transparent 1px); background-size: 26px 26px;" />
      <div class="relative page-container py-12 sm:py-14 text-center">
        <p class="text-xs font-semibold uppercase tracking-[0.2em] text-primary-200 mb-3">Track · ट्र्याक गर्नुहोस्</p>
        <h1 class="text-3xl sm:text-4xl font-extrabold mb-3 tracking-tight">Where is my gunaso?</h1>
        <p class="text-blue-200 text-sm sm:text-base max-w-lg mx-auto mb-7">
          Enter your reference number to see its status and full, tamper-proof history.
        </p>
        <form class="max-w-lg mx-auto flex gap-2" @submit.prevent="handleTrack">
          <label for="ref-input" class="sr-only">Reference number</label>
          <input id="ref-input" v-model="reference" type="text" placeholder="GUN-2026-12345" autocomplete="off" spellcheck="false"
            class="flex-1 min-w-0 px-5 py-3.5 rounded-xl border border-white/20 bg-white/10 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-white/30 focus:bg-white/15 text-sm font-mono uppercase tracking-wider backdrop-blur-sm transition-all" />
          <button type="submit" :disabled="submissionStore.loading || !reference.trim()"
            class="px-6 py-3.5 bg-primary hover:bg-primary-600 text-white font-semibold rounded-xl transition-colors disabled:opacity-50 whitespace-nowrap">
            Track
          </button>
        </form>
        <p v-if="reference && !REF_PATTERN.test(normalize(reference))" class="text-blue-300/80 text-xs mt-3">
          References look like GUN-2026-12345.
        </p>
      </div>
    </div>

    <div class="page-container py-8 sm:py-10">
      <!-- Loading -->
      <div v-if="submissionStore.loading" class="max-w-3xl mx-auto space-y-4" aria-busy="true">
        <div class="card p-6 space-y-4">
          <div class="skeleton h-4 w-40" />
          <div class="skeleton h-6 w-3/4" />
          <div class="skeleton h-10 w-full" />
        </div>
        <div class="card p-6 space-y-3">
          <div class="skeleton h-4 w-1/3" /><div class="skeleton h-16 w-full" />
        </div>
      </div>

      <!-- Not found -->
      <div v-else-if="searched && submissionStore.error" class="max-w-lg mx-auto text-center py-12">
        <div class="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-5">
          <svg class="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        </div>
        <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-2">We couldn't find that reference</h2>
        <p class="text-gray-500 dark:text-gray-400 text-sm mb-6">{{ submissionStore.error }}</p>
        <div class="flex flex-col sm:flex-row gap-3 justify-center">
          <RouterLink :to="{ name: 'Track' }" class="btn-secondary">Try another reference</RouterLink>
          <RouterLink to="/submit" class="btn-primary">File a new gunaso</RouterLink>
        </div>
      </div>

      <!-- Found -->
      <div v-else-if="searched && sub" class="max-w-3xl mx-auto grid gap-5">
        <div class="card p-5 sm:p-7 animate-fade-up">
          <div class="flex items-start justify-between gap-4 flex-wrap">
            <div class="min-w-0">
              <div class="flex items-center gap-2 flex-wrap mb-2">
                <span class="text-xs font-mono text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2.5 py-1 rounded-lg">{{ sub.reference_number }}</span>
                <span class="text-xs font-semibold text-gray-500 dark:text-gray-400">{{ typeIcon[sub.type] }} {{ typeLabel[sub.type] }}</span>
                <span v-if="sub.category" class="text-xs text-gray-400">· {{ sub.category }}</span>
              </div>
              <h2 class="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white leading-snug">{{ sub.title }}</h2>
              <p class="text-sm text-gray-500 dark:text-gray-400 mt-1.5">
                To
                <RouterLink :to="`/organizations/${sub.org_slug}`" class="font-semibold text-accent hover:underline">{{ sub.organization_name }}</RouterLink>
                <span v-if="sub.branch_name"> · {{ sub.branch_name }} branch</span>
                · {{ formatDate(sub.created_at) }}
              </p>
            </div>
            <StatusBadge :status="sub.status" />
          </div>

          <div class="mt-7 mb-2">
            <StatusProgress :status="sub.status" :timeline="sub.timeline || []" :created-at="sub.created_at" />
          </div>

          <div v-if="nextStep" :class="['mt-6 rounded-2xl border px-4 py-3.5', toneClass[nextStep.tone]]" role="status">
            <p class="text-sm font-bold">{{ nextStep.title }}</p>
            <p class="text-sm opacity-90 mt-0.5">{{ nextStep.body }}</p>
          </div>

          <details class="mt-5 group">
            <summary class="text-sm font-semibold text-gray-600 dark:text-gray-300 cursor-pointer hover:text-primary list-none flex items-center gap-1.5">
              <svg class="w-4 h-4 transition-transform group-open:rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
              </svg>
              What was reported
            </summary>
            <p class="mt-3 bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4 text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-line">{{ sub.description }}</p>
          </details>

          <div class="mt-5 pt-5 border-t border-gray-100 dark:border-gray-700 flex flex-wrap gap-2">
            <button class="btn-ghost !px-3 !py-2 text-sm" @click="copyLink(false)">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/></svg>
              Copy status link
            </button>
            <button v-if="sub.can_follow_up && followupKey" class="btn-ghost !px-3 !py-2 text-sm" @click="copyLink(true)">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/></svg>
              Copy private follow-up link
            </button>
            <button class="btn-ghost !px-3 !py-2 text-sm" @click="printPage">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
              Print
            </button>
          </div>
        </div>

        <!-- Rate the outcome -->
        <div v-if="canRate && (sub.can_follow_up || sub.satisfaction_score)" class="card p-5 sm:p-7 animate-fade-up">
          <h3 class="font-bold text-gray-900 dark:text-white">How did {{ sub.organization_name }} handle it?</h3>
          <template v-if="sub.satisfaction_score && !editingRating">
            <div class="flex items-center gap-3 mt-3">
              <span class="text-2xl text-amber-400 tracking-tight" :aria-label="`${sub.satisfaction_score} out of 5`">
                {{ '★'.repeat(sub.satisfaction_score) }}<span class="text-gray-200 dark:text-gray-600">{{ '★'.repeat(5 - sub.satisfaction_score) }}</span>
              </span>
              <span class="text-sm font-semibold text-gray-700 dark:text-gray-200">{{ ratingLabels[sub.satisfaction_score] }}</span>
            </div>
            <p v-if="sub.satisfaction_comment" class="text-sm text-gray-600 dark:text-gray-300 mt-2">“{{ sub.satisfaction_comment }}”</p>
            <button v-if="sub.can_follow_up" class="text-sm text-primary font-semibold hover:underline mt-3" @click="editingRating = true">Change my rating</button>
          </template>
          <form v-else-if="sub.can_follow_up" class="mt-3 space-y-3" @submit.prevent="sendRating">
            <div class="flex items-center gap-1" role="radiogroup" aria-label="Rating" @mouseleave="hoverRating = 0">
              <button v-for="n in 5" :key="n" type="button" role="radio" :aria-checked="rating === n" :aria-label="`${n} – ${ratingLabels[n]}`"
                class="text-3xl leading-none transition-transform hover:scale-110 focus-visible:scale-110"
                :class="(hoverRating || rating) >= n ? 'text-amber-400' : 'text-gray-200 dark:text-gray-600'"
                @mouseenter="hoverRating = n" @click="rating = n">★</button>
              <span class="ml-2 text-sm font-medium text-gray-500 dark:text-gray-400">{{ ratingLabels[hoverRating || rating] }}</span>
            </div>
            <textarea v-model="ratingComment" rows="2" maxlength="2000" class="input-base resize-none"
              placeholder="Anything to add? (optional — only you and the organization see this)" />
            <p v-if="ratingError" class="field-error">{{ ratingError }}</p>
            <button type="submit" :disabled="!rating || sendingRating" class="btn-primary !py-2.5">
              {{ sendingRating ? 'Saving…' : 'Submit rating' }}
            </button>
          </form>
        </div>

        <!-- Conversation -->
        <div class="card p-5 sm:p-7 animate-fade-up">
          <h3 class="font-bold text-gray-900 dark:text-white mb-5">Case history</h3>
          <SubmissionTimeline :timeline="sub.timeline || []" :organization-name="sub.organization_name" audience="citizen" />

          <div v-if="canReply" class="mt-7 pt-6 border-t border-gray-100 dark:border-gray-700">
            <label for="reply" class="label">Add a follow-up</label>
            <textarea id="reply" v-model="replyText" rows="3" maxlength="4000" class="input-base resize-none"
              placeholder="New information, a question, or tell them the problem is still happening…" />
            <p v-if="replyError" class="field-error">{{ replyError }}</p>
            <div class="flex items-center justify-between gap-3 mt-2.5 flex-wrap">
              <p class="text-xs text-gray-400 dark:text-gray-500">
                {{ sub.is_anonymous ? 'Sent anonymously — the organization never sees who you are.' : 'The organization will see this on the case.' }}
              </p>
              <button :disabled="replyText.trim().length < 2 || sendingReply" class="btn-primary !py-2.5 !px-5" @click="sendReply">
                {{ sendingReply ? 'Sending…' : 'Send follow-up' }}
              </button>
            </div>
          </div>
          <div v-else-if="!sub.can_follow_up && sub.status !== 'closed'"
            class="mt-7 pt-6 border-t border-gray-100 dark:border-gray-700 flex items-start gap-3 text-sm text-gray-500 dark:text-gray-400">
            <svg class="w-5 h-5 shrink-0 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
            </svg>
            <p>
              Filed this gunaso? Open the <strong class="text-gray-700 dark:text-gray-200">private follow-up link</strong> from your
              confirmation to reply or rate the outcome<template v-if="!authStore.isAuthenticated">, or
              <RouterLink :to="{ name: 'Login', query: { redirect: route.fullPath } }" class="text-primary font-semibold hover:underline">sign in</RouterLink>
              if you filed it from your account</template>.
            </p>
          </div>
        </div>
      </div>

      <!-- Nothing searched yet -->
      <div v-else class="max-w-3xl mx-auto">
        <div v-if="saved.entries.length" class="card p-5 sm:p-6 animate-fade-up">
          <div class="flex items-center justify-between mb-3">
            <h2 class="font-bold text-gray-900 dark:text-white">Filed from this device</h2>
            <span class="text-xs text-gray-400">Only stored in this browser</span>
          </div>
          <ul class="divide-y divide-gray-100 dark:divide-gray-700">
            <li v-for="entry in saved.entries" :key="entry.ref" class="flex items-center gap-3 py-3">
              <button class="flex-1 min-w-0 text-left group" @click="openSaved(entry)">
                <p class="font-mono text-xs text-gray-500 dark:text-gray-400">{{ entry.ref }}</p>
                <p class="text-sm font-semibold text-gray-800 dark:text-gray-100 truncate group-hover:text-primary">{{ entry.title || 'Untitled gunaso' }}</p>
                <p class="text-xs text-gray-400 truncate">{{ entry.organization }}</p>
              </button>
              <button class="p-2 rounded-lg text-gray-300 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20" :aria-label="`Forget ${entry.ref} on this device`" @click="saved.remove(entry.ref)">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </li>
          </ul>
        </div>
        <div v-else class="text-center py-12">
          <svg class="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          <p class="text-gray-600 dark:text-gray-300 text-sm font-medium">Your reference number is on your confirmation screen and email.</p>
          <p class="text-gray-400 dark:text-gray-500 text-sm mt-1">
            Signed in? <RouterLink to="/dashboard" class="text-primary font-semibold hover:underline">See all your gunaso</RouterLink>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
