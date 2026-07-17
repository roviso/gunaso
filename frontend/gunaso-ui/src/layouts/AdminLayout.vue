<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AdminSidebar from '@/components/AdminSidebar.vue'
import ToastNotification from '@/components/ToastNotification.vue'

const authStore = useAuthStore()
const router = useRouter()
const sidebarCollapsed = ref(false)

const menuOpen = ref(false)
const menuRef = ref(null)

async function handleLogout() {
  menuOpen.value = false
  await authStore.logout()
  router.push({ name: 'Login' })
}

function handleClickOutside(e) {
  if (menuRef.value && !menuRef.value.contains(e.target)) {
    menuOpen.value = false
  }
}

onMounted(() => document.addEventListener('mousedown', handleClickOutside))
onUnmounted(() => document.removeEventListener('mousedown', handleClickOutside))
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-app-bg dark:bg-gray-900 font-sans">
    <AdminSidebar :collapsed="sidebarCollapsed" @toggle="sidebarCollapsed = !sidebarCollapsed" />

    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <!-- Top bar -->
      <header class="h-14 bg-white dark:bg-gray-800 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between px-4 shrink-0 z-10 shadow-sm">
        <button
          @click="sidebarCollapsed = !sidebarCollapsed"
          class="p-2 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
          </svg>
        </button>

        <span class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 font-semibold hidden sm:flex">
          <span class="px-2 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
            God Mode
          </span>
          Platform Control Room
        </span>

        <div class="flex items-center gap-1">
          <div ref="menuRef" class="relative ml-1">
            <button
              @click="menuOpen = !menuOpen"
              class="flex items-center gap-2 px-2 py-1.5 rounded-lg text-gray-500 dark:text-gray-400 hover:text-secondary dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-sm font-medium">
              <div class="w-7 h-7 rounded-full bg-amber-500 text-gray-950 flex items-center justify-center text-xs font-bold shrink-0">
                {{ authStore.userInitial }}
              </div>
              <span class="hidden sm:block max-w-[140px] truncate">{{ authStore.user?.name || 'Superadmin' }}</span>
              <svg :class="['w-4 h-4 text-gray-400 transition-transform duration-200', menuOpen ? 'rotate-180' : '']"
                fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </button>

            <Transition name="menu">
              <div v-if="menuOpen"
                class="absolute right-0 top-full mt-1.5 w-56 bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-100 dark:border-gray-700 overflow-hidden z-50">
                <div class="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
                  <p class="text-xs text-gray-500 dark:text-gray-400">Signed in as</p>
                  <p class="text-sm font-semibold text-gray-900 dark:text-white truncate">{{ authStore.user?.email }}</p>
                </div>
                <div class="py-1">
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
        </div>
      </header>

      <!-- Main content -->
      <main class="flex-1 overflow-y-auto">
        <RouterView />
      </main>
    </div>

    <ToastNotification />
  </div>
</template>

<style scoped>
.menu-enter-active, .menu-leave-active { transition: all 0.15s ease; }
.menu-enter-from, .menu-leave-to { opacity: 0; transform: translateY(-6px) scale(0.97); }
</style>
