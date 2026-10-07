import api from './index'

export const submissionsAPI = {
  create: (formData) => api.post('/submissions/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  // The private follow-up key travels in a header, never the query string,
  // so it stays out of server access logs (see TrackSubmissionView).
  track: (reference, key) => api.get(`/submissions/track/${encodeURIComponent(reference)}/`, {
    headers: key ? { 'X-Followup-Key': key } : {},
  }),
  // Submitter-only follow-ups: the signed-in owner, or whoever holds the key.
  reply: (reference, message, key) => api.post(
    `/submissions/track/${encodeURIComponent(reference)}/reply/`, { message, key: key || '' }
  ),
  rateOutcome: (reference, score, comment, key) => api.post(
    `/submissions/track/${encodeURIComponent(reference)}/feedback/`, { score, comment: comment || '', key: key || '' }
  ),
  mySubmissions: (params) => api.get('/submissions/my/', { params }),
  getByReference: (reference) => api.get(`/submissions/${encodeURIComponent(reference)}/`),
  updateStatus: (reference, data) => api.patch(`/submissions/${encodeURIComponent(reference)}/status/`, data),
  // internal=true → organization-only note, never shown to or emailed to the citizen.
  addNote: (reference, note, internal = false) => api.post(
    `/submissions/${encodeURIComponent(reference)}/updates/`, { note, internal }
  ),
  assign: (reference, data) => api.patch(`/submissions/${encodeURIComponent(reference)}/assign/`, data),
  setVisibility: (reference, isPublic) => api.patch(`/submissions/${encodeURIComponent(reference)}/visibility/`, { is_public: isPublic }),
  updateCategory: (reference, category) => api.patch(`/submissions/${encodeURIComponent(reference)}/category/`, { category }),
  // 503 = AI not configured for this deployment, 502 = the AI request itself
  // failed — both distinct from a generic error so the UI can say why.
  aiClassify: (reference) => api.post(`/submissions/${encodeURIComponent(reference)}/ai-classify/`),
  aiSuggestion: (reference) => api.post(`/submissions/${encodeURIComponent(reference)}/ai-suggestion/`),
  orgSubmissions: (params) => api.get('/org/submissions/', { params }),
  orgStats: () => api.get('/org/stats/'),
  // Same filters as orgSubmissions; returns a CSV blob.
  exportCsv: (params) => api.get('/org/submissions/export/', { params, responseType: 'blob', timeout: 60000 }),
  // days: 7 | 30 | 90 | undefined (all time)
  mapFeed: (params) => api.get('/org/map-feed/', { params })
}
