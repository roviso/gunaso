import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/', name: 'Home', component: () => import('@/views/LandingPage.vue') },
  { path: '/organizations', name: 'Organizations', component: () => import('@/views/OrganizationsPage.vue') },
  { path: '/organizations/:slug', name: 'OrganizationDetail', component: () => import('@/views/OrganizationDetailPage.vue') },
  { path: '/submit', name: 'Submit', component: () => import('@/views/SubmitPage.vue') },
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
    path: '/dashboard', name: 'Dashboard',
    component: () => import('@/views/CitizenDashboardPage.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/org/dashboard', name: 'OrgDashboard',
    component: () => import('@/views/OrgDashboardPage.vue'),
    meta: { requiresAuth: true, orgAdmin: true }
  },
  { path: '/org/register', name: 'OrgRegister', component: () => import('@/views/OrgRegisterPage.vue') },
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

router.beforeEach((to, _from, next) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return next({ name: 'Login', query: { redirect: to.fullPath } })
  }
  if (to.meta.orgAdmin && !auth.isOrgAdmin) {
    return next({ name: 'Dashboard' })
  }
  if (to.meta.guest && auth.isAuthenticated) {
    return next(auth.isOrgAdmin ? { name: 'OrgDashboard' } : { name: 'Dashboard' })
  }
  next()
})

export default router
