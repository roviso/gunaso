import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/', name: 'Home', component: () => import('@/views/LandingPage.vue') },
  { path: '/organizations', name: 'Organizations', component: () => import('@/views/OrganizationsPage.vue') },
  { path: '/organizations/:slug', name: 'OrganizationDetail', component: () => import('@/views/OrganizationDetailPage.vue') },
  { path: '/map', name: 'OrganizationsMap', component: () => import('@/views/OrganizationsMapPage.vue') },
  { path: '/submit', name: 'Submit', component: () => import('@/views/SubmitPage.vue') },
  { path: '/submit/:orgSlug', name: 'SubmitForOrg', component: () => import('@/views/SubmitPage.vue') },
  { path: '/track', name: 'Track', component: () => import('@/views/TrackPage.vue') },
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
    ]
  },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0, behavior: 'smooth' }
  }
})

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return next({ name: 'Login', query: { redirect: to.fullPath } })
  }

  if (auth.isAuthenticated && auth.mustChangePassword && to.name !== 'ChangePassword') {
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
