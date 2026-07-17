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

  const roles = ref([])
  const rolesLoading = ref(false)
  const rolesError = ref(null)

  const privilegeCatalog = ref([])
  const privilegeCatalogLoading = ref(false)
  const privilegeCatalogError = ref(null)

  const qrCode = ref(null)
  const qrLoading = ref(false)
  const qrError = ref(null)

  const dashboardStats = ref(null)
  const statsLoading = ref(false)

  const showcase = ref([])
  const showcaseLoading = ref(false)
  const showcaseError = ref(null)

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

  async function inviteStaff(slug, payload) {
    const { data } = await organizationsAPI.inviteStaff(slug, payload)
    staff.value = [...staff.value, data]
    return data
  }

  async function createStaffWithCredentials(slug, payload) {
    const { data } = await organizationsAPI.createStaffWithCredentials(slug, payload)
    staff.value = [...staff.value, data]
    return data
  }

  async function resendInvite(slug, staffId) {
    const { data } = await organizationsAPI.resendInvite(slug, staffId)
    const idx = staff.value.findIndex((s) => s.id === staffId)
    if (idx !== -1) staff.value[idx] = { ...staff.value[idx], ...data }
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

  async function fetchRoles(slug) {
    rolesLoading.value = true
    rolesError.value = null
    try {
      const { data } = await organizationsAPI.listRoles(slug)
      roles.value = data.results || data
    } catch (err) {
      rolesError.value = apiErrorMessage(err, 'Could not load staff roles.')
      roles.value = []
    } finally {
      rolesLoading.value = false
    }
  }

  async function createRole(slug, payload) {
    rolesError.value = null
    try {
      const { data } = await organizationsAPI.createRole(slug, payload)
      roles.value = [...roles.value, data]
      return data
    } catch (err) {
      rolesError.value = apiErrorMessage(err, 'Could not create role.')
      throw err
    }
  }

  async function updateRole(slug, roleId, payload) {
    rolesError.value = null
    try {
      const { data } = await organizationsAPI.updateRole(slug, roleId, payload)
      const idx = roles.value.findIndex((r) => r.id === roleId)
      if (idx !== -1) roles.value[idx] = { ...roles.value[idx], ...data }
      return data
    } catch (err) {
      rolesError.value = apiErrorMessage(err, 'Could not update role.')
      throw err
    }
  }

  async function deleteRole(slug, roleId) {
    rolesError.value = null
    try {
      await organizationsAPI.deleteRole(slug, roleId)
      roles.value = roles.value.filter((r) => r.id !== roleId)
    } catch (err) {
      rolesError.value = apiErrorMessage(err, 'Could not delete role.')
      throw err
    }
  }

  async function fetchPrivilegeCatalog() {
    privilegeCatalogLoading.value = true
    privilegeCatalogError.value = null
    try {
      const { data } = await organizationsAPI.getPrivilegeCatalog()
      privilegeCatalog.value = data.results || data
    } catch (err) {
      privilegeCatalogError.value = apiErrorMessage(err, 'Could not load the privilege catalog.')
      privilegeCatalog.value = []
    } finally {
      privilegeCatalogLoading.value = false
    }
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

  // Re-fetch currentOrg without toggling `loading`, so in-place refreshes
  // (e.g. after rating) don't flash the full-page spinner.
  async function refreshCurrentOrg(slug) {
    try {
      const { data } = await organizationsAPI.getBySlug(slug)
      currentOrg.value = data
    } catch {
      // Non-critical: keep showing the last known org data.
    }
  }

  async function updateSettings(slug, payload) {
    const { data } = await organizationsAPI.updateSettings(slug, payload)
    currentOrg.value = { ...currentOrg.value, ...data }
    return data
  }

  async function fetchShowcase(slug, params = {}) {
    showcaseLoading.value = true
    showcaseError.value = null
    try {
      const { data } = await organizationsAPI.getShowcase(slug, params)
      showcase.value = data.results || data
    } catch (err) {
      showcaseError.value = apiErrorMessage(err, 'Could not load public submissions.')
      showcase.value = []
    } finally {
      showcaseLoading.value = false
    }
  }

  return {
    organizations, currentOrg, loading, error, totalCount,
    staff, staffLoading, staffError,
    roles, rolesLoading, rolesError,
    privilegeCatalog, privilegeCatalogLoading, privilegeCatalogError,
    qrCode, qrLoading, qrError,
    dashboardStats, statsLoading,
    showcase, showcaseLoading, showcaseError,
    fetchOrganizations, fetchOrgBySlug, fetchMyOrg, refreshCurrentOrg, updateSettings,
    fetchStaff, inviteStaff, createStaffWithCredentials, resendInvite, removeStaff, updateStaffRole,
    fetchRoles, createRole, updateRole, deleteRole,
    fetchPrivilegeCatalog,
    fetchQRCode, fetchStats, fetchShowcase,
  }
})
