<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useOrganizationStore } from '@/stores/organization'
import StatusBadge from '@/components/StatusBadge.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const router = useRouter()
const orgStore = useOrganizationStore()

const mockSubmissions = ref([
  { id: 1, title: 'Internet disconnected without notice', category: 'Network Issue', status: 'resolved', created_at: '2024-03-15' },
  { id: 2, title: 'Overcharged on monthly bill', category: 'Billing', status: 'in_review', created_at: '2024-03-12' },
  { id: 3, title: 'Poor customer service experience', category: 'Customer Service', status: 'pending', created_at: '2024-03-10' },
  { id: 4, title: 'Speed much lower than advertised', category: 'Data Speed', status: 'resolved', created_at: '2024-03-08' },
  { id: 5, title: 'Appreciation for quick resolution', category: 'Feedback', status: 'resolved', created_at: '2024-03-05' },
])

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

const bgColors = ['bg-red-500', 'bg-blue-500', 'bg-violet-500', 'bg-emerald-500', 'bg-orange-500', 'bg-cyan-500']
const logoBg = computed(() => bgColors[(orgStore.currentOrg?.id || 0) % bgColors.length])

onMounted(() => orgStore.fetchOrgBySlug(route.params.slug))
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
          <div class="grid grid-cols-3 divide-x divide-gray-200 dark:divide-gray-700 text-center">
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
          </div>
        </div>
      </div>

      <!-- Content -->
      <div class="page-container py-8">
        <div class="max-w-3xl">
          <h2 class="section-title mb-5">Recent Public Submissions</h2>
          <div class="space-y-3">
            <div v-for="sub in mockSubmissions" :key="sub.id"
              class="card p-4 flex items-center gap-4">
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-900 dark:text-white truncate">{{ sub.title }}</p>
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{{ sub.category }} · {{ formatDate(sub.created_at) }}</p>
              </div>
              <StatusBadge :status="sub.status" />
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
