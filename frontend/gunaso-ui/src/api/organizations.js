import api from './index'

export const organizationsAPI = {
  list: (params) => api.get('/organizations/', { params }),
  getBySlug: (slug) => api.get(`/organizations/${slug}/`),
  register: (data) => api.post('/organizations/', data),
  getStats: (slug) => api.get(`/organizations/${slug}/stats/`),
  getSubmissions: (slug, params) => api.get(`/organizations/${slug}/submissions/`, { params })
}
