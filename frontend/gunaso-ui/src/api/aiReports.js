import api from './index'

export const aiReportsAPI = {
  list: () => api.get('/org/ai-reports/'),
  generate: (dateFrom, dateTo) => api.post('/org/ai-reports/', { date_from: dateFrom, date_to: dateTo }),
}
