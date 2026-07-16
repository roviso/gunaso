import api from './index'

export const organizationsAPI = {
  list: (params) => api.get('/organizations/', { params }),
  getBySlug: (slug) => api.get(`/organizations/${slug}/`),
  getMine: () => api.get('/organizations/mine/'),
  register: (data) => api.post('/organizations/', data),
  getStats: (slug) => api.get(`/organizations/${slug}/stats/`),
  getSubmissions: (slug, params) => api.get(`/organizations/${slug}/submissions/`, { params }),
  // Public showcase: submissions staff have opted to display on the org's
  // public profile (Submission.is_public) — no auth required.
  getShowcase: (slug, params) => api.get(`/organizations/${slug}/showcase/`, { params }),
  getStaff: (slug) => api.get(`/organizations/${slug}/staff/`),
  // Adds a staff member by email: attaches an existing usable-password user
  // immediately, or creates a pending user + emails a single-use invite link.
  // Replaces the old fixed-role-enum `addStaff`.
  inviteStaff: (slug, data) => api.post(`/organizations/${slug}/staff/`, data),
  // Alternative to inviteStaff: admin sets username/password/email directly,
  // account is active immediately with a forced password change + unverified
  // email. See apps/organizations/services.py::create_staff_with_credentials.
  createStaffWithCredentials: (slug, data) => api.post(`/organizations/${slug}/staff/`, { ...data, mode: 'credentials' }),
  resendInvite: (slug, staffId) => api.post(`/organizations/${slug}/staff/${staffId}/resend-invite/`),
  removeStaff: (slug, staffId) => api.delete(`/organizations/${slug}/staff/${staffId}/`),
  updateStaffRole: (slug, staffId, data) => api.patch(`/organizations/${slug}/staff/${staffId}/`, data),

  // Custom, admin-defined staff roles (each carrying its own privilege set).
  listRoles: (slug) => api.get(`/organizations/${slug}/roles/`),
  createRole: (slug, data) => api.post(`/organizations/${slug}/roles/`, data),
  updateRole: (slug, roleId, data) => api.patch(`/organizations/${slug}/roles/${roleId}/`, data),
  deleteRole: (slug, roleId) => api.delete(`/organizations/${slug}/roles/${roleId}/`),

  // Static catalog of privilege keys/labels/groups available to build a role from.
  getPrivilegeCatalog: () => api.get('/organizations/privileges/'),

  // Invite-link onboarding: preview (AllowAny) then accept (sets password, logs in).
  previewInvite: (token) => api.get(`/organizations/invite/${token}/`),
  acceptInvite: (token, data) => api.post(`/organizations/invite/${token}/accept/`, data),

  // origin lets the backend encode the URL the visitor is actually browsing on
  // (e.g. an ngrok tunnel) instead of the configured FRONTEND_URL.
  getQRCode: (slug) => api.get(`/organizations/${slug}/qrcode/`, {
    params: { format: 'base64', origin: window.location.origin },
  }),
}
