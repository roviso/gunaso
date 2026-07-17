import api from './index'

// Superadmin dashboard endpoints (/api/v1/admin/*) — every call here requires
// User.is_superuser on the backend (apps/platform_admin/permissions.py::IsSuperAdmin).
export const adminAPI = {
  getOverview: () => api.get('/admin/overview/'),

  listOrganizations: (params) => api.get('/admin/organizations/', { params }),
  // Body may include either or both of `is_verified`/`is_active`.
  updateOrganization: (slug, data) => api.patch(`/admin/organizations/${slug}/`, data),
  getOrganizationStaff: (slug) => api.get(`/admin/organizations/${slug}/staff/`),

  listUsers: (params) => api.get('/admin/users/', { params }),
  blockUser: (userId) => api.post(`/admin/users/${userId}/block/`),
  unblockUser: (userId) => api.post(`/admin/users/${userId}/unblock/`),
  promoteUser: (userId) => api.post(`/admin/users/${userId}/promote/`),
  demoteUser: (userId) => api.post(`/admin/users/${userId}/demote/`),

  listSubmissions: (params) => api.get('/admin/submissions/', { params }),
  listAuditLog: (params) => api.get('/admin/audit-log/', { params }),
}
