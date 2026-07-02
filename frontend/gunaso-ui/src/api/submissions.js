import api from './index'

export const submissionsAPI = {
  create: (formData) => api.post('/submissions/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  track: (reference) => api.get(`/submissions/track/${reference}/`),
  mySubmissions: (params) => api.get('/submissions/my/', { params }),
  getById: (id) => api.get(`/submissions/${id}/`),
  updateStatus: (id, data) => api.patch(`/submissions/${id}/status/`, data),
  addNote: (id, note) => api.post(`/submissions/${id}/notes/`, { note }),
  orgSubmissions: (params) => api.get('/org/submissions/', { params }),
  orgStats: () => api.get('/org/stats/')
}
