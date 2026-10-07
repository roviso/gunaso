import api from './index'

// Public, unauthenticated surfaces used by the marketing pages.
export const publicAPI = {
  // Aggregate, identity-free platform numbers (verified orgs only; cached server-side).
  stats: () => api.get('/public/stats/'),
  // Recently showcased cases (Submission.is_public) across verified orgs.
  stories: () => api.get('/public/stories/'),
  // Contact form → superadmin inbox. `website` is a honeypot and must stay empty.
  contact: (data) => api.post('/contact/', data),
}
