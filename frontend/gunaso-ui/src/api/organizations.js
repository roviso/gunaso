import api from './index'

export const organizationsAPI = {
  list: (params) => api.get('/organizations/', { params }),
  getBySlug: (slug) => api.get(`/organizations/${slug}/`),
  getMine: () => api.get('/organizations/mine/'),
  register: (data) => api.post('/organizations/', data),
  getStats: (slug) => api.get(`/organizations/${slug}/stats/`),
  getSubmissions: (slug, params) => api.get(`/organizations/${slug}/submissions/`, { params }),
  getStaff: (slug) => api.get(`/organizations/${slug}/staff/`),
  addStaff: (slug, data) => api.post(`/organizations/${slug}/staff/`, data),
  removeStaff: (slug, staffId) => api.delete(`/organizations/${slug}/staff/${staffId}/`),
  updateStaffRole: (slug, staffId, data) => api.patch(`/organizations/${slug}/staff/${staffId}/`, data),
  // origin lets the backend encode the URL the visitor is actually browsing on
  // (e.g. an ngrok tunnel) instead of the configured FRONTEND_URL.
  getQRCode: (slug) => api.get(`/organizations/${slug}/qrcode/`, {
    params: { format: 'base64', origin: window.location.origin },
  }),
}
