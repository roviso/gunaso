import { defineStore } from 'pinia'
import { ref } from 'vue'
import { aiReportsAPI } from '@/api/aiReports'
import { apiErrorMessage } from '@/api/index'

export const useAIReportsStore = defineStore('aiReports', () => {
  const reports = ref([])
  const loading = ref(false)
  const error = ref(null)
  const generating = ref(false)

  async function fetchReports() {
    loading.value = true
    error.value = null
    try {
      const { data } = await aiReportsAPI.list()
      reports.value = data.results || data
    } catch (err) {
      error.value = apiErrorMessage(err, 'Could not load AI reports.')
      reports.value = []
    } finally {
      loading.value = false
    }
  }

  // Errors are re-thrown (not stored on `error`) — the caller (report page's
  // generate button) shows 503/502 inline rather than via the list banner.
  async function generateReport(dateFrom, dateTo) {
    generating.value = true
    try {
      const { data } = await aiReportsAPI.generate(dateFrom, dateTo)
      reports.value = [data, ...reports.value]
      return data
    } finally {
      generating.value = false
    }
  }

  return { reports, loading, error, generating, fetchReports, generateReport }
})
