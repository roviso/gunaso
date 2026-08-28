import api from './index'

export const authAPI = {
  login: (credentials) => api.post('/auth/login/', credentials),
  register: (data) => api.post('/auth/register/', data),
  me: () => api.get('/auth/me/'),
  updateMe: (data) => api.patch('/auth/me/', data),
  logout: () => api.post('/auth/logout/'),
  refresh: () => api.post('/auth/refresh/'),
  // The current user's *active* OrganizationStaff membership — organization,
  // role name, and privileges — kept separate from `me()`'s org_admin-only
  // organization_name/organization_slug fields (see apps/organizations/views.py
  // ::MyStaffAccessView). Always resolves, never 404s: a user with no
  // qualifying membership gets null/empty fields back.
  getMyOrgAccess: () => api.get('/organizations/my-access/'),

  // Forced first-login flow for admin-created staff accounts (must_change_password).
  changePassword: (data) => api.post('/auth/change-password/', data),

  // Forgot password. Both calls are unauthenticated: the emailed uid/token
  // pair *is* the credential, and the link is typically opened from a mail
  // client with no session. requestPasswordReset always resolves 200 — the
  // backend deliberately doesn't say whether the address matched an account.
  requestPasswordReset: (email) => api.post('/auth/password-reset/', { email }),
  confirmPasswordReset: ({ uid, token, newPassword }) =>
    api.post('/auth/password-reset/confirm/', { uid, token, new_password: newPassword }),

  // Verifying an admin-typed email: request sends a link (optionally
  // correcting the address in the same call), confirm resolves the token
  // from that link. Confirm is intentionally unauthenticated on the backend.
  requestEmailVerification: (data) => api.post('/auth/email-verification/request/', data),
  confirmEmailVerification: (token) => api.post('/auth/email-verification/confirm/', { token }),
}
