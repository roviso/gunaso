import { defineStore } from 'pinia'
import { ref } from 'vue'
import { organizationsAPI } from '@/api/organizations'
import { apiErrorMessage } from '@/api/index'

export const useOrganizationStore = defineStore('organization', () => {
  const organizations = ref([])
  const currentOrg = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const totalCount = ref(0)

  const staff = ref([])
  const staffLoading = ref(false)
  const staffError = ref(null)

  const qrCode = ref(null)
  const qrLoading = ref(false)
  const qrError = ref(null)

  const dashboardStats = ref(null)
  const statsLoading = ref(false)

  async function fetchOrganizations(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await organizationsAPI.list(params)
      organizations.value = data.results || data
      totalCount.value = data.count ?? organizations.value.length
    } catch (err) {
      error.value = apiErrorMessage(err, 'Could not load organizations.')
      organizations.value = []
      totalCount.value = 0
    } finally {
      loading.value = false
    }
  }

  async function fetchOrgBySlug(slug) {
    loading.value = true
    error.value = null
    currentOrg.value = null
    try {
      const { data } = await organizationsAPI.getBySlug(slug)
      currentOrg.value = data
    } catch (err) {
      error.value = apiErrorMessage(err, 'Organization not found.')
    } finally {
      loading.value = false
    }
  }

  async function fetchMyOrg() {
    loading.value = true
    error.value = null
    try {
      const { data } = await organizationsAPI.getMine()
      currentOrg.value = data
      return data
    } catch (err) {
      error.value = apiErrorMessage(err, 'Could not load your organization.')
    } finally {
      loading.value = false
    }
  }

  async function fetchStaff(slug) {
    staffLoading.value = true
    staffError.value = null
    try {
      const { data } = await organizationsAPI.getStaff(slug)
      staff.value = data.results || data
    } catch (err) {
      staffError.value = apiErrorMessage(err, 'Could not load staff members.')
      staff.value = []
    } finally {
      staffLoading.value = false
    }
  }

  async function addStaff(slug, payload) {
    const { data } = await organizationsAPI.addStaff(slug, payload)
    staff.value = [...staff.value, data]
    return data
  }

  async function removeStaff(slug, staffId) {
    await organizationsAPI.removeStaff(slug, staffId)
    staff.value = staff.value.filter((s) => s.id !== staffId)
  }

  async function updateStaffRole(slug, staffId, role) {
    const { data } = await organizationsAPI.updateStaffRole(slug, staffId, { role })
    const idx = staff.value.findIndex((s) => s.id === staffId)
    if (idx !== -1) staff.value[idx] = { ...staff.value[idx], ...data }
    return data
  }

  async function fetchQRCode(slug) {
    qrLoading.value = true
    qrError.value = null
    try {
      const { data } = await organizationsAPI.getQRCode(slug)
      qrCode.value = data
    } catch (err) {
      qrError.value = apiErrorMessage(err, 'Could not load QR code.')
    } finally {
      qrLoading.value = false
    }
  }

  async function fetchStats(slug) {
    statsLoading.value = true
    try {
      const { data } = await organizationsAPI.getStats(slug)
      dashboardStats.value = data
    } catch {
      dashboardStats.value = null
    } finally {
      statsLoading.value = false
    }
  }

  return {
    organizations, currentOrg, loading, error, totalCount,
    staff, staffLoading, staffError,
    qrCode, qrLoading, qrError,
    dashboardStats, statsLoading,
    fetchOrganizations, fetchOrgBySlug, fetchMyOrg,
    fetchStaff, addStaff, removeStaff, updateStaffRole,
    fetchQRCode, fetchStats,
  }
})
