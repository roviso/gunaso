<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useOrganizationStore } from '@/stores/organization'
import OrgSidebar from '@/components/OrgSidebar.vue'
import ToastNotification from '@/components/ToastNotification.vue'
import EmailVerificationBanner from '@/components/EmailVerificationBanner.vue'

const authStore = useAuthStore()
const orgStore = useOrganizationStore()
const router = useRouter()
const sidebarCollapsed = ref(false)

const orgMenuOpen = ref(false)
const orgMenuRef = ref(null)

async function handleLogout() {
  orgMenuOpen.value = false
  await authStore.logout()
  router.push({ name: 'Login' })
}

function handleClickOutside(e) {
  if (orgMenuRef.value && !orgMenuRef.value.contains(e.target)) {
    orgMenuOpen.value = false
  }
}

onMounted(() => document.addEventListener('mousedown', handleClickOutside))
onUnmounted(() => document.removeEventListener('mousedown', handleClickOutside))

onMounted(async () => {
  if (orgStore.currentOrg) return

  if (authStore.isOrgAdmin) {
    const org = await orgStore.fetchMyOrg()
    if (!org) router.replace({ name: 'OrgRegister' })
    return
  }

  // Staff never manage an org (/organizations/mine/ 404s for them — it's
  // scoped to `organization.admin`), so resolve their org via the active
  // staff membership the router guard already fetched instead. Redirecting
  // to OrgRegister here would be wrong — staff don't register orgs.
  if (authStore.accessibleOrgSlug) {
    await orgStore.fetchOrgBySlug(authStore.accessibleOrgSlug)
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

        <span class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 font-semibold hidden sm:flex">
          {{ orgStore.currentOrg?.name || authStore.user?.organization_name || 'Organization Portal' }}
          <span v-if="orgStore.currentOrg && !orgStore.currentOrg.is_verified"
            class="px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
            title="A platform admin needs to verify this organization before it appears in public search.">
            Pending verification
          </span>
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

          <!-- Org / account menu -->
          <div ref="orgMenuRef" class="relative ml-1">
            <button
              @click="orgMenuOpen = !orgMenuOpen"
              class="flex items-center gap-2 px-2 py-1.5 rounded-lg text-gray-500 dark:text-gray-400 hover:text-secondary dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-sm font-medium">
              <div class="w-7 h-7 rounded-full bg-secondary text-white flex items-center justify-center text-xs font-bold shrink-0">
                {{ authStore.userInitial }}
              </div>
              <span class="hidden sm:block max-w-[140px] truncate">{{ authStore.user?.name || 'Admin' }}</span>
              <svg :class="['w-4 h-4 text-gray-400 transition-transform duration-200', orgMenuOpen ? 'rotate-180' : '']"
                fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </button>

            <Transition name="menu">
              <div v-if="orgMenuOpen"
                class="absolute right-0 top-full mt-1.5 w-56 bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-100 dark:border-gray-700 overflow-hidden z-50">
                <div v-if="orgStore.currentOrg" class="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
                  <p class="text-xs text-gray-500 dark:text-gray-400">Organization</p>
                  <p class="text-sm font-semibold text-gray-900 dark:text-white truncate">{{ orgStore.currentOrg.name }}</p>
                </div>
                <div class="py-1">
                  <RouterLink v-if="orgStore.currentOrg"
                    :to="`/organizations/${orgStore.currentOrg.slug}`"
                    @click="orgMenuOpen = false"
                    class="flex items-center gap-2.5 px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                    </svg>
                    Organization Profile
                  </RouterLink>
                  <RouterLink
                    to="/org/settings"
                    @click="orgMenuOpen = false"
                    class="flex items-center gap-2.5 px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                    </svg>
                    Settings
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
        </div>
      </header>

      <EmailVerificationBanner />

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
