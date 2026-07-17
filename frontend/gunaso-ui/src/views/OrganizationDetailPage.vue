<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useOrganizationStore } from '@/stores/organization'
import { useUIStore } from '@/stores/ui'
import { organizationsAPI } from '@/api/organizations'
import { apiErrorMessage } from '@/api/index'
import StatusBadge from '@/components/StatusBadge.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import StarRating from '@/components/StarRating.vue'
import SubmissionTimeline from '@/components/SubmissionTimeline.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const orgStore = useOrganizationStore()
const uiStore = useUIStore()

const expandedRef = ref(null)

const myScore = ref(null)
const ratingBusy = ref(false)

async function loadMyRating() {
  if (!authStore.isAuthenticated) return
  try {
    const { data } = await organizationsAPI.getMyRating(route.params.slug)
    myScore.value = data.score
  } catch {
    // Non-critical — the rate control just starts empty.
  }
}

async function submitRating(score) {
  if (ratingBusy.value) return
  ratingBusy.value = true
  try {
    await organizationsAPI.rateOrganization(route.params.slug, score)
    myScore.value = score
    uiStore.showSuccess('Thanks for rating!')
    await orgStore.refreshCurrentOrg(route.params.slug)
  } catch (err) {
    uiStore.showError(apiErrorMessage(err, 'Could not save your rating.'))
  } finally {
    ratingBusy.value = false
  }
}

async function removeRating() {
  if (ratingBusy.value) return
  ratingBusy.value = true
  try {
    await organizationsAPI.deleteRating(route.params.slug)
    myScore.value = null
    await orgStore.refreshCurrentOrg(route.params.slug)
  } catch (err) {
    uiStore.showError(apiErrorMessage(err, 'Could not remove your rating.'))
  } finally {
    ratingBusy.value = false
  }
}

function toggleExpand(sub) {
  expandedRef.value = expandedRef.value === sub.reference_number ? null : sub.reference_number
}

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

const bgColors = ['bg-red-500', 'bg-blue-500', 'bg-violet-500', 'bg-emerald-500', 'bg-orange-500', 'bg-cyan-500']
const logoBg = computed(() => bgColors[(orgStore.currentOrg?.id || 0) % bgColors.length])

onMounted(async () => {
  await orgStore.fetchOrgBySlug(route.params.slug)
  if (orgStore.currentOrg) {
    orgStore.fetchShowcase(route.params.slug)
    loadMyRating()
  }
})
</script>

<template>
  <div class="bg-app-bg dark:bg-gray-900 min-h-screen">
    <LoadingSpinner v-if="orgStore.loading" :fullPage="true" />

    <template v-else-if="orgStore.currentOrg">
      <!-- Org Hero -->
      <div class="bg-white dark:bg-gray-800 border-b border-gray-100 dark:border-gray-700 shadow-sm">
        <div class="page-container py-8">
          <button @click="router.back()" class="flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 mb-5 transition-colors">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
            </svg>
            Back to Organizations
          </button>

          <div class="flex flex-col sm:flex-row items-start gap-5">
            <div :class="['w-16 h-16 rounded-2xl flex items-center justify-center text-white font-extrabold text-2xl shrink-0', logoBg]">
              {{ orgStore.currentOrg.name[0] }}
            </div>
            <div class="flex-1">
              <div class="flex flex-wrap items-center gap-2 mb-1">
                <h1 class="text-2xl font-extrabold text-secondary dark:text-white">{{ orgStore.currentOrg.name }}</h1>
                <div v-if="orgStore.currentOrg.verified" class="flex items-center gap-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs font-semibold px-2.5 py-1 rounded-full">
                  <svg class="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                  </svg>
                  Verified
                </div>
                <span class="bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-xs font-medium px-2.5 py-1 rounded-full">
                  {{ orgStore.currentOrg.category }}
                </span>
              </div>
              <div v-if="orgStore.currentOrg.average_rating != null" class="flex items-center gap-1.5 mb-2">
                <StarRating :model-value="orgStore.currentOrg.average_rating" readonly size="sm" />
                <span class="text-sm font-semibold text-gray-700 dark:text-gray-200">{{ orgStore.currentOrg.average_rating }}</span>
                <span class="text-xs text-gray-400">({{ orgStore.currentOrg.rating_count }} rating{{ orgStore.currentOrg.rating_count === 1 ? '' : 's' }})</span>
              </div>
              <p class="text-gray-600 dark:text-gray-400 text-sm leading-relaxed mb-3 max-w-2xl">
                {{ orgStore.currentOrg.description }}
              </p>
              <a v-if="orgStore.currentOrg.website" :href="orgStore.currentOrg.website" target="_blank"
                class="inline-flex items-center gap-1.5 text-accent hover:underline text-sm font-medium">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                </svg>
                {{ orgStore.currentOrg.website }}
              </a>
            </div>
            <RouterLink :to="{ name: 'Submit', query: { org: orgStore.currentOrg.slug } }"
              class="btn-primary shrink-0">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
              </svg>
              Submit Complaint
            </RouterLink>
          </div>
        </div>
      </div>

      <!-- Stats Bar -->
      <div class="bg-white dark:bg-gray-800 border-b border-gray-100 dark:border-gray-700">
        <div class="page-container py-5">
          <div :class="['grid divide-x divide-gray-200 dark:divide-gray-700 text-center',
            orgStore.currentOrg.average_rating != null ? 'grid-cols-2 sm:grid-cols-4' : 'grid-cols-3']">
            <div class="px-4">
              <p class="text-2xl font-extrabold text-secondary dark:text-white">{{ orgStore.currentOrg.submission_count?.toLocaleString() }}</p>
              <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Total Submissions</p>
            </div>
            <div class="px-4">
              <p :class="['text-2xl font-extrabold', orgStore.currentOrg.resolved_percent >= 80 ? 'text-green-600' : orgStore.currentOrg.resolved_percent >= 60 ? 'text-amber-600' : 'text-red-500']">
                {{ orgStore.currentOrg.resolved_percent }}%
              </p>
              <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Resolution Rate</p>
            </div>
            <div class="px-4">
              <p class="text-2xl font-extrabold text-secondary dark:text-white">{{ orgStore.currentOrg.avg_resolution_days }}d</p>
              <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Avg. Response</p>
            </div>
            <div v-if="orgStore.currentOrg.average_rating != null" class="px-4">
              <p class="text-2xl font-extrabold text-amber-500">{{ orgStore.currentOrg.average_rating }}<span class="text-sm text-gray-400 font-semibold">/5</span></p>
              <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Citizen Rating</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Content -->
      <div class="page-container py-8">
        <div class="max-w-3xl">
          <!-- Rate this organization -->
          <div class="card p-5 mb-8 flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-6">
            <div class="flex-1">
              <h2 class="text-sm font-bold text-gray-900 dark:text-white">
                {{ myScore ? 'Your rating' : 'Rate this organization' }}
              </h2>
              <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                {{ authStore.isAuthenticated
                  ? 'How well does this organization handle citizen concerns?'
                  : 'Sign in to share how well this organization handles citizen concerns.' }}
              </p>
            </div>
            <div v-if="authStore.isAuthenticated" class="flex items-center gap-3">
              <StarRating :model-value="myScore" size="lg" @update:model-value="submitRating" />
              <button v-if="myScore" @click="removeRating" :disabled="ratingBusy"
                class="text-xs text-gray-400 hover:text-red-500 transition-colors disabled:opacity-50">
                Remove
              </button>
            </div>
            <RouterLink v-else :to="{ name: 'Login', query: { redirect: route.fullPath } }"
              class="btn-secondary !px-4 !py-2 text-sm shrink-0">
              Sign in to rate
            </RouterLink>
          </div>

          <h2 class="section-title mb-1">Public Showcase</h2>
          <p class="text-sm text-gray-500 dark:text-gray-400 mb-5">
            Submissions this organization has chosen to share publicly, and how they were handled.
          </p>

          <LoadingSpinner v-if="orgStore.showcaseLoading" />

          <div v-else-if="!orgStore.showcase.length" class="card p-10 text-center">
            <p class="text-gray-500 dark:text-gray-400 text-sm">
              No public submissions yet — this organization hasn't showcased any complaints or feedback.
            </p>
          </div>

          <div v-else class="space-y-3">
            <div v-for="sub in orgStore.showcase" :key="sub.reference_number"
              @click="toggleExpand(sub)"
              class="card-interactive p-4"
              :class="{ 'ring-2 ring-primary/30 border-primary/30': expandedRef === sub.reference_number }">
              <div class="flex items-center gap-4">
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-gray-900 dark:text-white truncate">{{ sub.title }}</p>
                  <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    {{ sub.category || sub.type }} · {{ sub.submitter_name || 'Anonymous' }} · {{ formatDate(sub.created_at) }}
                  </p>
                </div>
                <StatusBadge :status="sub.status" />
              </div>

              <Transition name="slide">
                <div v-if="expandedRef === sub.reference_number" class="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700" @click.stop>
                  <p class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed mb-4">{{ sub.description }}</p>
                  <p class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">How it was handled</p>
                  <SubmissionTimeline :timeline="sub.timeline || []" />
                </div>
              </Transition>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Not found -->
    <div v-else class="page-container py-16 text-center">
      <p class="text-gray-500 dark:text-gray-400">{{ orgStore.error || 'Organization not found.' }}</p>
      <RouterLink to="/organizations" class="btn-primary mt-4 inline-flex">Browse Organizations</RouterLink>
    </div>
  </div>
</template>

<style scoped>
.slide-enter-active, .slide-leave-active { transition: all 0.2s ease; }
.slide-enter-from, .slide-leave-to { opacity: 0; transform: translateY(-6px); }
</style>
