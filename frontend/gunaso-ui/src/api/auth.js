import api from './index'

export const authAPI = {
  login: (credentials) => api.post('/auth/login/', credentials),
  register: (data) => api.post('/auth/register/', data),
  me: () => api.get('/auth/me/'),
  logout: () => api.post('/auth/logout/'),
  refreshToken: (refresh) => api.post('/auth/token/refresh/', { refresh })
}
