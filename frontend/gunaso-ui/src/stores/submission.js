import { defineStore } from 'pinia'
import { ref } from 'vue'
import { submissionsAPI } from '@/api/submissions'

const MOCK_SUBMISSIONS = [
  {
    id: 1, reference_number: 'GUN-2024-00001',
    title: 'Internet disconnection for 3 days without notice',
    type: 'complaint', category: 'Network Issue', priority: 'high',
    status: 'in_review', organization_name: 'Nepal Telecom', org_slug: 'nepal-telecom',
    created_at: '2024-03-15T10:30:00Z', updated_at: '2024-03-17T14:00:00Z',
    description: 'My internet connection has been down for 3 consecutive days with no explanation from the provider. Multiple calls to customer service went unanswered.',
    timeline: [
      { status: 'submitted', note: 'Complaint submitted successfully.', created_at: '2024-03-15T10:30:00Z', updated_by: 'System' },
      { status: 'in_review', note: 'Your complaint has been assigned to our technical team for investigation.', created_at: '2024-03-17T14:00:00Z', updated_by: 'Support Team' }
    ]
  },
  {
    id: 2, reference_number: 'GUN-2024-00042',
    title: 'Overcharged Rs. 500 on monthly bill — no justification given',
    type: 'complaint', category: 'Billing', priority: 'medium',
    status: 'resolved', organization_name: 'Ncell', org_slug: 'ncell',
    created_at: '2024-03-10T08:00:00Z', updated_at: '2024-03-14T11:00:00Z',
    description: 'I was charged Rs. 500 extra on my monthly bill. The amount does not correspond to any service I subscribed to.',
    timeline: [
      { status: 'submitted', note: 'Complaint submitted.', created_at: '2024-03-10T08:00:00Z', updated_by: 'System' },
      { status: 'in_review', note: 'Billing team is investigating the discrepancy.', created_at: '2024-03-12T09:00:00Z', updated_by: 'Billing Support' },
      { status: 'resolved', note: 'We have identified the overcharge. A refund of Rs. 500 has been processed to your account.', created_at: '2024-03-14T11:00:00Z', updated_by: 'Billing Support' }
    ]
  },
  {
    id: 3, reference_number: 'GUN-2024-00089',
    title: 'Daily power outage every morning for two weeks',
    type: 'complaint', category: 'Service Disruption', priority: 'urgent',
    status: 'pending', organization_name: 'Nepal Electricity Authority', org_slug: 'nea',
    created_at: '2024-03-18T06:00:00Z', updated_at: '2024-03-18T06:00:00Z',
    description: 'Our ward has been experiencing daily power outages from 6am to 10am for the past two weeks. No prior notice was given.',
    timeline: [
      { status: 'submitted', note: 'Complaint submitted.', created_at: '2024-03-18T06:00:00Z', updated_by: 'System' }
    ]
  }
]

const MOCK_ORG_SUBMISSIONS = [
  ...MOCK_SUBMISSIONS,
  {
    id: 4, reference_number: 'GUN-2024-00103', title: 'Poor signal quality in Lalitpur district',
    type: 'complaint', category: 'Coverage', priority: 'medium',
    status: 'pending', organization_name: 'Nepal Telecom', org_slug: 'nepal-telecom',
    created_at: '2024-03-19T09:15:00Z', updated_at: '2024-03-19T09:15:00Z',
    submitter_name: 'R. Thapa', description: 'Very poor 4G signal at Patan Dhoka area.',
    timeline: [{ status: 'submitted', note: 'Complaint submitted.', created_at: '2024-03-19T09:15:00Z', updated_by: 'System' }]
  },
  {
    id: 5, reference_number: 'GUN-2024-00117', title: 'Excellent customer service — thank you!',
    type: 'feedback', category: 'Customer Service', priority: 'low',
    status: 'resolved', organization_name: 'Nepal Telecom', org_slug: 'nepal-telecom',
    created_at: '2024-03-20T14:00:00Z', updated_at: '2024-03-21T10:00:00Z',
    submitter_name: 'A. Shrestha', description: 'The agent resolved my issue in one call. Very impressed.',
    timeline: [
      { status: 'submitted', note: 'Feedback submitted.', created_at: '2024-03-20T14:00:00Z', updated_by: 'System' },
      { status: 'resolved', note: 'Thank you for your positive feedback!', created_at: '2024-03-21T10:00:00Z', updated_by: 'Support Team' }
    ]
  }
]

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
      error.value = err.response?.data || 'Submission failed.'
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
    } catch {
      const found = MOCK_SUBMISSIONS.find(
        (s) => s.reference_number.toLowerCase() === reference.toLowerCase()
      )
      if (found) {
        currentSubmission.value = found
      } else {
        error.value = 'No submission found with that reference number. Please double-check and try again.'
        throw new Error('Not found')
      }
    } finally {
      loading.value = false
    }
  }

  async function fetchMySubmissions() {
    loading.value = true
    error.value = null
    try {
      const { data } = await submissionsAPI.mySubmissions()
      submissions.value = data.results || data
    } catch {
      submissions.value = MOCK_SUBMISSIONS
    } finally {
      loading.value = false
    }
  }

  async function fetchOrgSubmissions(params = {}) {
    loading.value = true
    try {
      const { data } = await submissionsAPI.orgSubmissions(params)
      orgSubmissions.value = data.results || data
    } catch {
      orgSubmissions.value = MOCK_ORG_SUBMISSIONS
    } finally {
      loading.value = false
    }
  }

  async function fetchOrgStats() {
    try {
      const { data } = await submissionsAPI.orgStats()
      orgStats.value = data
    } catch {
      orgStats.value = {
        total: 156, pending: 43, in_review: 28,
        resolved_month: 67, avg_resolution_days: 6
      }
    }
  }

  async function updateStatus(id, payload) {
    loading.value = true
    try {
      const { data } = await submissionsAPI.updateStatus(id, payload)
      const idx = orgSubmissions.value.findIndex((s) => s.id === id)
      if (idx !== -1) {
        orgSubmissions.value[idx] = { ...orgSubmissions.value[idx], ...data }
      }
      if (currentSubmission.value?.id === id) {
        currentSubmission.value = { ...currentSubmission.value, ...data }
      }
      return data
    } catch {
      // Optimistic update for prototype
      const updatedItem = { status: payload.status, updated_at: new Date().toISOString() }
      const idx = orgSubmissions.value.findIndex((s) => s.id === id)
      if (idx !== -1) {
        orgSubmissions.value[idx] = { ...orgSubmissions.value[idx], ...updatedItem }
        if (payload.note) {
          orgSubmissions.value[idx].timeline = [
            ...(orgSubmissions.value[idx].timeline || []),
            { status: payload.status, note: payload.note, created_at: new Date().toISOString(), updated_by: 'Organization' }
          ]
        }
      }
    } finally {
      loading.value = false
    }
  }

  return {
    submissions, currentSubmission, orgSubmissions, orgStats, loading, error,
    createSubmission, fetchByReference, fetchMySubmissions,
    fetchOrgSubmissions, fetchOrgStats, updateStatus
  }
})
