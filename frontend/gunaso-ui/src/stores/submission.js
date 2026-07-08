import { defineStore } from 'pinia'
import { ref } from 'vue'
import { submissionsAPI } from '@/api/submissions'
import { apiErrorMessage } from '@/api/index'

export const useSubmissionStore = defineStore('submission', () => {
  const submissions = ref([])
  const currentSubmission = ref(null)
  const orgSubmissions = ref([])
  const orgStats = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function createSubmission(payload) {
    loading.value = true
    error.value = null
    try {
      const formData = new FormData()
      Object.entries(payload).forEach(([k, v]) => {
        if (v !== null && v !== undefined && v !== '') formData.append(k, v)
      })
      const { data } = await submissionsAPI.create(formData)
      return data
    } catch (err) {
      error.value = apiErrorMessage(err, 'Submission failed. Please try again.')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchByReference(reference) {
    loading.value = true
    error.value = null
    currentSubmission.value = null
    try {
      const { data } = await submissionsAPI.track(reference)
      currentSubmission.value = data
    } catch (err) {
      error.value = apiErrorMessage(
        err,
        'No submission found with that reference number. Please double-check and try again.'
      )
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchMySubmissions(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await submissionsAPI.mySubmissions(params)
      submissions.value = data.results || data
    } catch (err) {
      error.value = apiErrorMessage(err, 'Could not load your submissions.')
      submissions.value = []
    } finally {
      loading.value = false
    }
  }

  async function fetchOrgSubmissions(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await submissionsAPI.orgSubmissions(params)
      orgSubmissions.value = data.results || data
    } catch (err) {
      error.value = apiErrorMessage(err, 'Could not load organization submissions.')
      orgSubmissions.value = []
    } finally {
      loading.value = false
    }
  }

  async function fetchOrgStats() {
    try {
      const { data } = await submissionsAPI.orgStats()
      orgStats.value = data
    } catch {
      orgStats.value = null
    }
  }

  async function updateStatus(reference, payload) {
    loading.value = true
    try {
      const { data } = await submissionsAPI.updateStatus(reference, payload)
      const idx = orgSubmissions.value.findIndex((s) => s.reference_number === reference)
      if (idx !== -1) orgSubmissions.value[idx] = data
      if (currentSubmission.value?.reference_number === reference) {
        currentSubmission.value = data
      }
      return data
    } catch (err) {
      error.value = apiErrorMessage(err, 'Failed to update status.')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function addNote(reference, note) {
    try {
      const { data } = await submissionsAPI.addNote(reference, note)
      return data
    } catch (err) {
      error.value = apiErrorMessage(err, 'Failed to add note.')
      throw err
    }
  }

  async function assignSubmission(reference, staffId) {
    try {
      const { data } = await submissionsAPI.assign(reference, { staff_id: staffId })
      const idx = orgSubmissions.value.findIndex((s) => s.reference_number === reference)
      if (idx !== -1) orgSubmissions.value[idx] = data
      if (currentSubmission.value?.reference_number === reference) currentSubmission.value = data
      return data
    } catch (err) {
      error.value = apiErrorMessage(err, 'Failed to assign submission.')
      throw err
    }
  }

  return {
    submissions, currentSubmission, orgSubmissions, orgStats, loading, error,
    createSubmission, fetchByReference, fetchMySubmissions,
    fetchOrgSubmissions, fetchOrgStats, updateStatus, addNote, assignSubmission,
  }
})
