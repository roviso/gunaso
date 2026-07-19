<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useAIReportsStore } from '@/stores/aiReports'
import { useUIStore } from '@/stores/ui'
import { apiErrorMessage } from '@/api/index'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const authStore = useAuthStore()
const reportsStore = useAIReportsStore()
const uiStore = useUIStore()

const canView = computed(() => authStore.hasPrivilege('view_stats'))

function defaultDates() {
  const to = new Date()
  const from = new Date()
  from.setDate(from.getDate() - 30)
  return { from: from.toISOString().slice(0, 10), to: to.toISOString().slice(0, 10) }
}

const range = ref(defaultDates())
const generateError = ref('')
const expandedId = ref(null)

async function submitGenerate() {
  if (reportsStore.generating) return
  generateError.value = ''
  try {
    const report = await reportsStore.generateReport(range.value.from, range.value.to)
    expandedId.value = report.id
    uiStore.showSuccess('Report generated.')
  } catch (err) {
    generateError.value = apiErrorMessage(err, 'Could not generate the report right now.')
  }
}

function toggle(id) {
  expandedId.value = expandedId.value === id ? null : id
}

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

onMounted(async () => {
  if (canView.value) await reportsStore.fetchReports()
})
</script>

<template>
  <div class="p-6 space-y-5 max-w-4xl">
    <div>
      <h1 class="text-xl font-extrabold text-secondary dark:text-white">AI Reports</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
        Summarize a period's gunaso into themes, sentiment, and concrete recommendations — bilingual, Nepali and English.
      </p>
    </div>

    <div v-if="!canView" class="card p-6 text-sm text-gray-600 dark:text-gray-300">
      You don't have permission to view reports for this organization.
    </div>

    <template v-else>
      <!-- Generate -->
      <div class="card p-5">
        <h2 class="text-sm font-bold text-gray-800 dark:text-white mb-3">Generate a New Report</h2>
        <div class="flex flex-wrap items-end gap-3">
          <div>
            <label class="label">From</label>
            <input v-model="range.from" type="date" class="input-base w-auto" />
          </div>
          <div>
            <label class="label">To</label>
            <input v-model="range.to" type="date" class="input-base w-auto" />
          </div>
          <button @click="submitGenerate" :disabled="reportsStore.generating"
            class="btn-primary !px-5 text-sm disabled:opacity-50">
            <svg v-if="reportsStore.generating" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            {{ reportsStore.generating ? 'Generating…' : '🤖 Generate Report' }}
          </button>
        </div>
        <p v-if="generateError" class="field-error mt-2">{{ generateError }}</p>
      </div>

      <LoadingSpinner v-if="reportsStore.loading" />

      <div v-else-if="reportsStore.error" class="card p-6 text-center text-sm text-red-500 dark:text-red-400">
        {{ reportsStore.error }}
      </div>

      <div v-else-if="!reportsStore.reports.length" class="card p-10 text-center">
        <p class="font-semibold text-gray-700 dark:text-gray-200">No reports yet</p>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Pick a date range above and generate your first one.</p>
      </div>

      <div v-else class="space-y-3">
        <div v-for="report in reportsStore.reports" :key="report.id" class="card overflow-hidden">
          <button @click="toggle(report.id)" class="w-full flex items-center justify-between gap-4 p-4 text-left hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
            <div class="min-w-0">
              <p class="text-sm font-semibold text-gray-900 dark:text-white">
                {{ formatDate(report.date_from) }} – {{ formatDate(report.date_to) }}
              </p>
              <p class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                {{ report.submission_count }} gunaso · {{ formatDate(report.created_at) }}
                <span v-if="report.created_by_name"> · by {{ report.created_by_name }}</span>
              </p>
            </div>
            <svg :class="['w-4 h-4 text-gray-400 shrink-0 transition-transform duration-200', expandedId === report.id ? 'rotate-180' : '']"
              fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
            </svg>
          </button>

          <div v-if="expandedId === report.id" class="border-t border-gray-100 dark:border-gray-700 p-5 space-y-5">
            <!-- Executive summary -->
            <div>
              <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2">Executive Summary</h3>
              <p class="text-sm text-gray-800 dark:text-gray-200 leading-relaxed">{{ report.summary_nepali }}</p>
              <p class="text-sm text-gray-600 dark:text-gray-400 leading-relaxed mt-2 pt-2 border-t border-gray-100 dark:border-gray-700">
                {{ report.summary_english }}
              </p>
            </div>

            <!-- Themes -->
            <div v-if="report.themes?.length">
              <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2">Top Themes</h3>
              <div class="space-y-2">
                <div v-for="theme in report.themes" :key="theme.name" class="flex items-start gap-3 p-2.5 rounded-lg bg-gray-50 dark:bg-gray-700/40">
                  <span class="shrink-0 px-2 py-0.5 rounded-full text-xs font-bold bg-primary/10 text-primary">{{ theme.count }}</span>
                  <div class="min-w-0">
                    <p class="text-sm font-semibold text-gray-900 dark:text-white">{{ theme.name }}</p>
                    <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{{ theme.summary }}</p>
                  </div>
                </div>
              </div>
            </div>

            <!-- Sentiment -->
            <div v-if="report.sentiment_overview">
              <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2">Sentiment</h3>
              <p class="text-sm text-gray-700 dark:text-gray-300">{{ report.sentiment_overview }}</p>
            </div>

            <!-- Recommendations -->
            <div v-if="report.recommendations?.length">
              <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2">Recommendations</h3>
              <ul class="space-y-1.5">
                <li v-for="(rec, i) in report.recommendations" :key="i" class="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <span class="text-primary shrink-0">→</span>
                  {{ rec }}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
