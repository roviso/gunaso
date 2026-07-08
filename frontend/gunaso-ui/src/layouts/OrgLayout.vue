<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useOrganizationStore } from '@/stores/organization'
import OrgSidebar from '@/components/OrgSidebar.vue'
import ToastNotification from '@/components/ToastNotification.vue'

const authStore = useAuthStore()
const orgStore = useOrganizationStore()
const router = useRouter()
const sidebarCollapsed = ref(false)

async function handleLogout() {
  await authStore.logout()
  router.push({ name: 'Login' })
}

onMounted(async () => {
  if (!orgStore.currentOrg) {
    await orgStore.fetchMyOrg()
  }
})
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-app-bg dark:bg-gray-900 font-sans">
    <OrgSidebar :collapsed="sidebarCollapsed" @toggle="sidebarCollapsed = !sidebarCollapsed" />

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

        <span class="text-sm text-gray-600 dark:text-gray-300 font-semibold hidden sm:block">
          {{ orgStore.currentOrg?.name || authStore.user?.organization_name || 'Organization Portal' }}
        </span>

        <div class="flex items-center gap-1">
          <RouterLink
            to="/"
            class="p-2 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            title="Public site">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
            </svg>
          </RouterLink>

          <button
            @click="handleLogout"
            class="ml-1 flex items-center gap-2 px-3 py-1.5 rounded-lg text-gray-500 dark:text-gray-400 hover:text-secondary dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-sm font-medium"
            title="Sign out">
            <div class="w-7 h-7 rounded-full bg-secondary text-white flex items-center justify-center text-xs font-bold shrink-0">
              {{ authStore.userInitial }}
            </div>
            <span class="hidden sm:block">{{ authStore.user?.name || 'Admin' }}</span>
          </button>
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
