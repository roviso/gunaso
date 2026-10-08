import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const SITE_NAME = 'Gunaso'
const DEFAULT_DESCRIPTION =
  'File a complaint, feedback or suggestion to any registered organization in Nepal in under two minutes — ' +
  'anonymously if you want — and track it on a public, tamper-proof timeline until it is resolved.'

const routes = [
  {
    path: '/', name: 'Home', component: () => import('@/views/LandingPage.vue'),
    meta: { title: 'Every gunaso deserves an answer', description: DEFAULT_DESCRIPTION }
  },
  {
    path: '/organizations', name: 'Organizations', component: () => import('@/views/OrganizationsPage.vue'),
    meta: { title: 'Organizations', description: 'Browse verified organizations on Gunaso — see how fast they resolve complaints and how citizens rate them.' }
  },
  { path: '/organizations/:slug', name: 'OrganizationDetail', component: () => import('@/views/OrganizationDetailPage.vue'), meta: { title: 'Organization' } },
  {
    path: '/map', name: 'OrganizationsMap', component: () => import('@/views/OrganizationsMapPage.vue'),
    meta: { title: 'Map', description: 'Find the office or branch nearest to you and file a gunaso right from the map.', fullBleed: true }
  },
  {
    path: '/submit', name: 'Submit', component: () => import('@/views/SubmitPage.vue'),
    meta: { title: 'File a gunaso', description: 'Tell an organization what went wrong — no account needed, anonymous if you prefer.' }
  },
  { path: '/submit/:orgSlug', name: 'SubmitForOrg', component: () => import('@/views/SubmitPage.vue'), meta: { title: 'File a gunaso' } },
  {
    // :ref is optional so /track keeps working; the private follow-up key,
    // when present, rides in the URL fragment (#key=...) — never sent to servers.
    path: '/track/:ref?', name: 'Track', component: () => import('@/views/TrackPage.vue'),
    meta: { title: 'Track your gunaso', description: 'Check the status of your gunaso with its GUN- reference number.' }
  },
  {
    path: '/for-organizations', name: 'ForOrganizations', component: () => import('@/views/ForOrganizationsPage.vue'),
    meta: { title: 'For organizations', description: 'Turn complaints into a service-improvement engine: branch QR codes, staff roles, SLA alerts, AI insights and a public trust score.' }
  },
  {
    path: '/how-it-works', name: 'HowItWorks', component: () => import('@/views/HowItWorksPage.vue'),
    meta: { title: 'How it works & FAQ', description: 'How Gunaso works for citizens and organizations, and answers to common questions about privacy and anonymity.' }
  },
  {
    path: '/contact', name: 'Contact', component: () => import('@/views/ContactPage.vue'),
    meta: { title: 'Contact us', description: 'Questions, partnerships, or bringing your organization to Gunaso — get in touch.' }
  },
  { path: '/privacy', name: 'Privacy', component: () => import('@/views/LegalPage.vue'), props: { page: 'privacy' }, meta: { title: 'Privacy policy' } },
  { path: '/terms', name: 'Terms', component: () => import('@/views/LegalPage.vue'), props: { page: 'terms' }, meta: { title: 'Terms of use' } },
  { path: '/child-safety', name: 'ChildSafety', component: () => import('@/views/LegalPage.vue'), props: { page: 'child-safety' }, meta: { title: 'Child safety standards', description: 'Gunaso’s standards against child sexual abuse and exploitation, and how to report a concern.' } },
  {
    path: '/login', name: 'Login',
    component: () => import('@/views/LoginPage.vue'),
    meta: { guest: true }
  },
  {
    path: '/register', name: 'Register',
    component: () => import('@/views/RegisterPage.vue'),
    meta: { guest: true }
  },
  {
    path: '/forgot-password', name: 'ForgotPassword',
    component: () => import('@/views/ForgotPasswordPage.vue'),
    meta: { guest: true }
  },
  {
    // Public like /invite/:token — the uid/token pair from the email *is* the
    // credential, and the link is normally opened from a mail client with no
    // session. No `guest` meta either: someone signed in on this device may
    // still be resetting the password of the account the link belongs to.
    // Path must match apps/accounts/services.py::password_reset_link exactly.
    path: '/reset-password/:uid/:token', name: 'ResetPassword',
    component: () => import('@/views/ResetPasswordPage.vue')
  },
  {
    // Deliberately no requiresAuth/guest meta: an org admin who is already
    // signed in on this device may open a link inviting a *different* email,
    // and a signed-out visitor must be able to open it too — this route has
    // to be reachable either way.
    path: '/invite/:token', name: 'AcceptInvite',
    component: () => import('@/views/AcceptInvitePage.vue')
  },
  {
    path: '/welcome', name: 'Welcome',
    component: () => import('@/views/OnboardingPage.vue'),
    meta: { requiresAuth: true, fullPage: true }
  },
  {
    // Forced first-login step for admin-created staff accounts
    // (auth.mustChangePassword) — the global guard below redirects here
    // before any other authenticated route is reachable.
    path: '/change-password', name: 'ChangePassword',
    component: () => import('@/views/ChangePasswordPage.vue'),
    meta: { requiresAuth: true, fullPage: true }
  },
  {
    // Public like /invite/:token — may be opened signed-out, or signed-in
    // verifying a different session's email.
    path: '/verify-email/:token', name: 'VerifyEmail',
    component: () => import('@/views/VerifyEmailPage.vue')
  },
  {
    path: '/dashboard', name: 'Dashboard',
    component: () => import('@/views/CitizenDashboardPage.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/org/register', name: 'OrgRegister',
    component: () => import('@/views/OrgRegisterPage.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/org',
    component: () => import('@/layouts/OrgLayout.vue'),
    // orgAccess = org_admin OR an active org-staff membership (see
    // authStore.hasOrgAccess). Broadened from org_admin-only so staff members
    // added via the invite flow can reach /org/* — a staff invitee's
    // user_type stays 'citizen', so gating on user_type alone locked them
    // out entirely. Per-page/per-action privilege gating (view_staff,
    // manage_roles, manage_submissions, ...) happens inside each page/component.
    meta: { requiresAuth: true, orgAccess: true, fullPage: true },
    children: [
      { path: 'dashboard', name: 'OrgDashboard', component: () => import('@/views/OrgDashboardRouter.vue') },
      { path: 'submissions', name: 'OrgSubmissions', component: () => import('@/views/OrgSubmissionsPage.vue') },
      { path: 'staff', name: 'OrgStaff', component: () => import('@/views/OrgStaffPage.vue') },
      { path: 'roles', name: 'OrgRoles', component: () => import('@/views/OrgRolesPage.vue') },
      { path: 'branches', name: 'OrgBranches', component: () => import('@/views/OrgBranchesPage.vue') },
      { path: 'reports', name: 'OrgAIReports', component: () => import('@/views/OrgAIReportsPage.vue') },
      { path: 'map', name: 'OrgMap', component: () => import('@/views/OrgMapPage.vue') },
      { path: 'settings', name: 'OrgSettings', component: () => import('@/views/OrgSettingsPage.vue') },
      { path: 'qrcode', name: 'OrgQRCode', component: () => import('@/views/OrgQRCodePage.vue') },
    ]
  },
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    // superAdmin = User.is_superuser (apps/platform_admin/permissions.py::IsSuperAdmin) —
    // deliberately independent of orgAccess/isOrgAdmin; a superadmin doesn't
    // need to manage or belong to any organization.
    meta: { requiresAuth: true, superAdmin: true, fullPage: true },
    children: [
      { path: '', redirect: { name: 'AdminOverview' } },
      { path: 'overview', name: 'AdminOverview', component: () => import('@/views/AdminOverviewPage.vue') },
      { path: 'organizations', name: 'AdminOrganizations', component: () => import('@/views/AdminOrganizationsPage.vue') },
      { path: 'users', name: 'AdminUsers', component: () => import('@/views/AdminUsersPage.vue') },
      { path: 'submissions', name: 'AdminSubmissions', component: () => import('@/views/AdminSubmissionsPage.vue') },
      { path: 'audit-log', name: 'AdminAuditLog', component: () => import('@/views/AdminAuditLogPage.vue') },
      { path: 'inbox', name: 'AdminInbox', component: () => import('@/views/AdminInboxPage.vue') },
    ]
  },
  { path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('@/views/NotFoundPage.vue'), meta: { title: 'Page not found' } }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    // In-page anchors (/how-it-works#faq) — but never the track page's
    // #key=... fragment, which is a credential, not an element id.
    if (to.hash && !to.hash.startsWith('#key=')) return { el: to.hash, top: 80, behavior: 'smooth' }
    if (to.path === from.path) return false
    return { top: 0 }
  }
})

function setMetaDescription(content) {
  let tag = document.querySelector('meta[name="description"]')
  if (!tag) {
    tag = document.createElement('meta')
    tag.setAttribute('name', 'description')
    document.head.appendChild(tag)
  }
  tag.setAttribute('content', content)
}

router.afterEach((to) => {
  const title = to.meta.title
  document.title = title && to.name !== 'Home' ? `${title} · ${SITE_NAME}` : `${SITE_NAME} — ${title || 'Every gunaso deserves an answer'}`
  setMetaDescription(to.meta.description || DEFAULT_DESCRIPTION)
})

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return next({ name: 'Login', query: { redirect: to.fullPath } })
  }

  // ResetPassword is exempt alongside ChangePassword: both are ways to satisfy
  // the same requirement, and bouncing an emailed reset link back to the
  // forced-change screen would strand a user who came here precisely because
  // they don't have the temporary password any more.
  if (
    auth.isAuthenticated && auth.mustChangePassword &&
    to.name !== 'ChangePassword' && to.name !== 'ResetPassword'
  ) {
    return next({ name: 'ChangePassword' })
  }

  if (to.meta.superAdmin && !auth.isSuperAdmin) {
    return next(auth.hasOrgAccess ? { name: 'OrgDashboard' } : { name: 'Dashboard' })
  }

  if (to.meta.orgAccess) {
    // Staff access isn't knowable from the `user` object alone — it's a
    // separate lookup (authStore.fetchStaffAccess). Resolve it lazily, once,
    // right before we need it: org admins never need this (isOrgAdmin already
    // grants access) and most visitors never touch /org/* at all, so eagerly
    // fetching on every app boot would be wasted work for the common case.
    if (auth.isAuthenticated && !auth.isOrgAdmin && !auth.staffAccess.organization_slug && !auth.staffAccessLoading) {
      await auth.fetchStaffAccess()
    }
    if (!auth.hasOrgAccess) {
      return next({ name: 'Dashboard' })
    }
  }

  if (to.meta.guest && auth.isAuthenticated) {
    if (auth.isSuperAdmin) return next({ name: 'AdminOverview' })
    return next(auth.hasOrgAccess ? { name: 'OrgDashboard' } : { name: 'Dashboard' })
  }

  next()
})

export default router
