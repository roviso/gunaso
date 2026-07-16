import api from './index'

export const submissionsAPI = {
  create: (formData) => api.post('/submissions/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  track: (reference) => api.get(`/submissions/track/${encodeURIComponent(reference)}/`),
  mySubmissions: (params) => api.get('/submissions/my/', { params }),
  getByReference: (reference) => api.get(`/submissions/${encodeURIComponent(reference)}/`),
  updateStatus: (reference, data) => api.patch(`/submissions/${encodeURIComponent(reference)}/status/`, data),
  addNote: (reference, note) => api.post(`/submissions/${encodeURIComponent(reference)}/updates/`, { note }),
  assign: (reference, data) => api.patch(`/submissions/${encodeURIComponent(reference)}/assign/`, data),
  setVisibility: (reference, isPublic) => api.patch(`/submissions/${encodeURIComponent(reference)}/visibility/`, { is_public: isPublic }),
  orgSubmissions: (params) => api.get('/org/submissions/', { params }),
  orgStats: () => api.get('/org/stats/')
}
