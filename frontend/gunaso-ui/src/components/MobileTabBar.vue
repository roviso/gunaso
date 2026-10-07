<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// Native-app bottom navigation (rendered only inside the Capacitor shell).
const route = useRoute()
const authStore = useAuthStore()

const meTo = computed(() => {
  if (!authStore.isAuthenticated) return '/login'
  return authStore.hasOrgAccess ? '/org/dashboard' : '/dashboard'
})

const tabs = computed(() => [
  { name: 'Home', to: '/', match: (p) => p === '/',
    icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
  { name: 'Explore', to: '/organizations', match: (p) => p.startsWith('/organizations') || p.startsWith('/map'),
    icon: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4' },
  { name: 'Submit', to: '/submit', match: (p) => p.startsWith('/submit'), primary: true,
    icon: 'M12 4v16m8-8H4' },
  { name: 'Track', to: '/track', match: (p) => p.startsWith('/track'),
    icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4' },
  { name: authStore.isAuthenticated ? 'Me' : 'Sign in', to: meTo.value,
    match: (p) => ['/dashboard', '/login', '/register', '/forgot-password'].some((x) => p.startsWith(x)),
    icon: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z' },
])
</script>

<template>
  <nav aria-label="Primary"
    class="tab-bar fixed bottom-0 inset-x-0 z-50 pb-safe bg-white/95 dark:bg-gray-900/95 backdrop-blur border-t border-gray-100 dark:border-gray-800">
    <ul class="grid grid-cols-5 h-16">
      <li v-for="tab in tabs" :key="tab.name" class="flex">
        <RouterLink :to="tab.to" :aria-current="tab.match(route.path) ? 'page' : undefined"
          class="flex-1 flex flex-col items-center justify-center gap-1 text-[11px] font-semibold select-none transition-colors active:scale-95"
          :class="tab.match(route.path) ? 'text-primary' : 'text-gray-500 dark:text-gray-400'">
          <span v-if="tab.primary"
            class="-mt-6 w-14 h-14 rounded-2xl bg-primary text-white flex items-center justify-center shadow-lg shadow-primary/30 ring-4 ring-white dark:ring-gray-900">
            <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" :d="tab.icon" />
            </svg>
          </span>
          <svg v-else class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" :stroke-width="tab.match(route.path) ? 2.2 : 1.8" :d="tab.icon" />
          </svg>
          {{ tab.name }}
        </RouterLink>
      </li>
    </ul>
  </nav>
</template>
