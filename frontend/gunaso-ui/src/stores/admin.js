import { defineStore } from 'pinia'
import { ref } from 'vue'
import { adminAPI } from '@/api/admin'
import { apiErrorMessage } from '@/api/index'

export const useAdminStore = defineStore('admin', () => {
  const overview = ref(null)
  const overviewLoading = ref(false)
  const overviewError = ref(null)

  const organizations = ref([])
  const organizationsLoading = ref(false)
  const organizationsError = ref(null)
  const organizationsCount = ref(0)

  const orgStaff = ref([])
  const orgStaffLoading = ref(false)
  const orgStaffError = ref(null)

  const users = ref([])
  const usersLoading = ref(false)
  const usersError = ref(null)
  const usersCount = ref(0)

  const submissions = ref([])
  const submissionsLoading = ref(false)
  const submissionsError = ref(null)
  const submissionsCount = ref(0)

  const auditLog = ref([])
  const auditLogLoading = ref(false)
  const auditLogError = ref(null)
  const auditLogCount = ref(0)

  async function fetchOverview() {
    overviewLoading.value = true
    overviewError.value = null
    try {
      const { data } = await adminAPI.getOverview()
      overview.value = data
    } catch (err) {
      overviewError.value = apiErrorMessage(err, 'Could not load platform overview.')
    } finally {
      overviewLoading.value = false
    }
  }

  async function fetchOrganizations(params = {}) {
    organizationsLoading.value = true
    organizationsError.value = null
    try {
      const { data } = await adminAPI.listOrganizations(params)
      organizations.value = data.results || data
      organizationsCount.value = data.count ?? organizations.value.length
    } catch (err) {
      organizationsError.value = apiErrorMessage(err, 'Could not load organizations.')
      organizations.value = []
      organizationsCount.value = 0
    } finally {
      organizationsLoading.value = false
    }
  }

  async function updateOrganization(slug, payload) {
    const { data } = await adminAPI.updateOrganization(slug, payload)
    const idx = organizations.value.findIndex((o) => o.slug === slug)
    if (idx !== -1) organizations.value[idx] = { ...organizations.value[idx], ...data }
    return data
  }

  async function fetchOrganizationStaff(slug) {
    orgStaffLoading.value = true
    orgStaffError.value = null
    try {
      const { data } = await adminAPI.getOrganizationStaff(slug)
      orgStaff.value = data.results || data
    } catch (err) {
      orgStaffError.value = apiErrorMessage(err, 'Could not load staff for this organization.')
      orgStaff.value = []
    } finally {
      orgStaffLoading.value = false
    }
  }

  async function fetchUsers(params = {}) {
    usersLoading.value = true
    usersError.value = null
    try {
      const { data } = await adminAPI.listUsers(params)
      users.value = data.results || data
      usersCount.value = data.count ?? users.value.length
    } catch (err) {
      usersError.value = apiErrorMessage(err, 'Could not load users.')
      users.value = []
      usersCount.value = 0
    } finally {
      usersLoading.value = false
    }
  }

  function _patchUser(userId, data) {
    const idx = users.value.findIndex((u) => u.id === userId)
    if (idx !== -1) users.value[idx] = { ...users.value[idx], ...data }
  }

  async function blockUser(userId) {
    const { data } = await adminAPI.blockUser(userId)
    _patchUser(userId, data)
    return data
  }

  async function unblockUser(userId) {
    const { data } = await adminAPI.unblockUser(userId)
    _patchUser(userId, data)
    return data
  }

  async function promoteUser(userId) {
    const { data } = await adminAPI.promoteUser(userId)
    _patchUser(userId, data)
    return data
  }

  async function demoteUser(userId) {
    const { data } = await adminAPI.demoteUser(userId)
    _patchUser(userId, data)
    return data
  }

  async function fetchSubmissions(params = {}) {
    submissionsLoading.value = true
    submissionsError.value = null
    try {
      const { data } = await adminAPI.listSubmissions(params)
      submissions.value = data.results || data
      submissionsCount.value = data.count ?? submissions.value.length
    } catch (err) {
      submissionsError.value = apiErrorMessage(err, 'Could not load submissions.')
      submissions.value = []
      submissionsCount.value = 0
    } finally {
      submissionsLoading.value = false
    }
  }

  async function fetchAuditLog(params = {}) {
    auditLogLoading.value = true
    auditLogError.value = null
    try {
      const { data } = await adminAPI.listAuditLog(params)
      auditLog.value = data.results || data
      auditLogCount.value = data.count ?? auditLog.value.length
    } catch (err) {
      auditLogError.value = apiErrorMessage(err, 'Could not load the audit log.')
      auditLog.value = []
      auditLogCount.value = 0
    } finally {
      auditLogLoading.value = false
    }
  }

  return {
    overview, overviewLoading, overviewError, fetchOverview,
    organizations, organizationsLoading, organizationsError, organizationsCount,
    fetchOrganizations, updateOrganization,
    orgStaff, orgStaffLoading, orgStaffError, fetchOrganizationStaff,
    users, usersLoading, usersError, usersCount,
    fetchUsers, blockUser, unblockUser, promoteUser, demoteUser,
    submissions, submissionsLoading, submissionsError, submissionsCount, fetchSubmissions,
    auditLog, auditLogLoading, auditLogError, auditLogCount, fetchAuditLog,
  }
})
