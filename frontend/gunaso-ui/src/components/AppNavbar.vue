<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUIStore()

const mobileOpen = ref(false)
const userMenuOpen = ref(false)
const userMenuRef = ref(null)

const navLinks = [
  { name: 'Home', to: '/' },
  { name: 'Organizations', to: '/organizations' },
  { name: 'Map', to: '/map' },
  { name: 'Submit', to: '/submit' },
  { name: 'Track', to: '/track' },
]

function isActive(path) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

async function handleLogout() {
  await authStore.logout()
  userMenuOpen.value = false
  mobileOpen.value = false
  router.push('/')
}

function handleClickOutside(e) {
  if (userMenuRef.value && !userMenuRef.value.contains(e.target)) {
    userMenuOpen.value = false
  }
}

onMounted(() => document.addEventListener('mousedown', handleClickOutside))
onUnmounted(() => document.removeEventListener('mousedown', handleClickOutside))
</script>

<template>
  <nav class="bg-white dark:bg-gray-900 border-b border-gray-100 dark:border-gray-800 sticky top-0 z-50 shadow-sm">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16">

        <!-- Logo -->
        <RouterLink to="/" class="flex items-center gap-2 shrink-0" @click="mobileOpen = false">
          <div class="w-8 h-8 bg-primary rounded-lg flex items-center justify-center shadow-sm">
            <span class="text-white font-display font-extrabold text-sm leading-none">G</span>
          </div>
          <span class="font-display font-bold text-lg text-secondary dark:text-white tracking-tight">Gunaso</span>
        </RouterLink>

        <!-- Desktop Nav -->
        <div class="hidden md:flex items-center gap-0.5">
          <RouterLink v-for="link in navLinks" :key="link.to" :to="link.to"
            :class="['px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-150',
              isActive(link.to)
                ? 'bg-primary/10 text-primary'
                : 'text-gray-600 dark:text-gray-300 hover:text-secondary dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800']">
            {{ link.name }}
          </RouterLink>
        </div>

        <!-- Right Actions -->
        <div class="flex items-center gap-1.5">
          <!-- Dark mode toggle -->
          <button @click="uiStore.toggleDarkMode()"
            class="p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            :title="uiStore.darkMode ? 'Switch to light mode' : 'Switch to dark mode'"
            :aria-label="uiStore.darkMode ? 'Switch to light mode' : 'Switch to dark mode'">
            <!-- Sun -->
            <svg v-if="uiStore.darkMode" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>
            </svg>
            <!-- Moon -->
            <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
            </svg>
          </button>

          <!-- Guest buttons -->
          <template v-if="!authStore.isAuthenticated">
            <RouterLink to="/login"
              class="hidden sm:inline-flex text-sm font-medium text-gray-600 dark:text-gray-300 hover:text-secondary dark:hover:text-white px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
              Login
            </RouterLink>
            <RouterLink to="/register"
              class="hidden sm:inline-flex bg-primary hover:bg-primary-600 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors shadow-sm">
              Register
            </RouterLink>
          </template>

          <!-- User menu -->
          <div v-else ref="userMenuRef" class="relative">
            <button @click="userMenuOpen = !userMenuOpen"
              class="flex items-center gap-2 px-2.5 py-1.5 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
              <div class="w-7 h-7 bg-secondary rounded-full flex items-center justify-center shrink-0">
                <span class="text-white text-xs font-bold">{{ authStore.userInitial }}</span>
              </div>
              <span class="hidden sm:block text-sm font-medium text-gray-700 dark:text-gray-200 max-w-[120px] truncate">
                {{ authStore.user?.name || 'My Account' }}
              </span>
              <svg :class="['w-4 h-4 text-gray-400 transition-transform duration-200', userMenuOpen ? 'rotate-180' : '']"
                fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </button>

            <Transition name="menu">
              <div v-if="userMenuOpen"
                class="absolute right-0 top-full mt-1.5 w-52 bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-100 dark:border-gray-700 overflow-hidden z-50">
                <div class="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
                  <p class="text-xs text-gray-500 dark:text-gray-400">Signed in as</p>
                  <p class="text-sm font-semibold text-gray-900 dark:text-white truncate">{{ authStore.user?.email }}</p>
                </div>
                <div class="py-1">
                  <RouterLink
                    :to="authStore.hasOrgAccess ? '/org/dashboard' : '/dashboard'"
                    @click="userMenuOpen = false"
                    class="flex items-center gap-2.5 px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/>
                    </svg>
                    Dashboard
                  </RouterLink>
                  <button @click="handleLogout"
                    class="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
                    </svg>
                    Sign out
                  </button>
                </div>
              </div>
            </Transition>
          </div>

          <!-- Hamburger -->
          <button @click="mobileOpen = !mobileOpen"
            :aria-label="mobileOpen ? 'Close menu' : 'Open menu'" :aria-expanded="mobileOpen"
            class="md:hidden p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors ml-1">
            <svg v-if="!mobileOpen" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
            </svg>
            <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
      </div>

      <!-- Mobile Menu -->
      <Transition name="slide">
        <div v-if="mobileOpen" class="md:hidden pb-4 border-t border-gray-100 dark:border-gray-800 mt-1">
          <div class="pt-3 space-y-0.5">
            <RouterLink v-for="link in navLinks" :key="link.to" :to="link.to" @click="mobileOpen = false"
              :class="['flex items-center px-3 py-2.5 rounded-xl text-sm font-medium transition-colors',
                isActive(link.to) ? 'bg-primary/10 text-primary' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800']">
              {{ link.name }}
            </RouterLink>
          </div>
          <div v-if="!authStore.isAuthenticated" class="mt-4 flex gap-2 px-1">
            <RouterLink to="/login" @click="mobileOpen = false"
              class="flex-1 text-center py-2.5 border border-gray-200 dark:border-gray-600 rounded-xl text-sm font-semibold text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
              Login
            </RouterLink>
            <RouterLink to="/register" @click="mobileOpen = false"
              class="flex-1 text-center py-2.5 bg-primary rounded-xl text-sm font-semibold text-white hover:bg-primary-600 transition-colors">
              Register
            </RouterLink>
          </div>
        </div>
      </Transition>
    </div>
  </nav>
</template>

<style scoped>
.menu-enter-active, .menu-leave-active { transition: all 0.15s ease; }
.menu-enter-from, .menu-leave-to { opacity: 0; transform: translateY(-6px) scale(0.97); }
.slide-enter-active, .slide-leave-active { transition: all 0.2s ease; }
.slide-enter-from, .slide-leave-to { opacity: 0; transform: translateY(-8px); }
</style>
