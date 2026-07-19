<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useOrganizationStore } from '@/stores/organization'

const props = defineProps({
  collapsed: { type: Boolean, default: false }
})

defineEmits(['toggle'])

const route = useRoute()
const authStore = useAuthStore()
const orgStore = useOrganizationStore()

const orgInitial = computed(() => {
  const name = orgStore.currentOrg?.name || authStore.user?.organization_name || 'O'
  return name[0].toUpperCase()
})

function isActive(path) {
  return route.path === path || route.path.startsWith(path + '/')
}

// Org admins implicitly hold every privilege (see authStore.hasPrivilege);
// staff members only see nav links their role's privilege set actually grants
// — gated per-link rather than all-or-nothing.
const canViewStaff = computed(() => authStore.hasPrivilege('view_staff'))
const canManageRoles = computed(() => authStore.hasPrivilege('manage_roles'))
const canViewStats = computed(() => authStore.hasPrivilege('view_stats'))
</script>

<template>
  <aside
    :class="[
      'flex flex-col bg-secondary dark:bg-gray-900 text-white transition-all duration-300 shrink-0 z-20',
      collapsed ? 'w-16' : 'w-60'
    ]">
    <!-- Org header -->
    <div class="h-14 flex items-center border-b border-white/10 px-3 shrink-0">
      <RouterLink to="/org/dashboard" class="flex items-center gap-3 min-w-0">
        <div class="w-8 h-8 rounded-xl bg-primary flex items-center justify-center text-white font-bold text-sm shrink-0">
          {{ orgInitial }}
        </div>
        <Transition name="fade">
          <div v-if="!collapsed" class="min-w-0 overflow-hidden">
            <p class="text-sm font-bold text-white truncate leading-tight">
              {{ orgStore.currentOrg?.name || authStore.user?.organization_name || 'Organization' }}
            </p>
            <p class="text-xs text-white/40">Admin Portal</p>
          </div>
        </Transition>
      </RouterLink>
    </div>

    <!-- Nav links -->
    <nav class="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
      <!-- Dashboard -->
      <RouterLink to="/org/dashboard"
        :class="[
          'flex items-center gap-3 px-2.5 py-2.5 rounded-xl transition-all duration-150',
          isActive('/org/dashboard')
            ? 'bg-white/15 text-white'
            : 'text-white/60 hover:bg-white/10 hover:text-white'
        ]">
        <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"/>
        </svg>
        <Transition name="fade">
          <span v-if="!collapsed" class="text-sm font-medium truncate">Dashboard</span>
        </Transition>
        <Transition name="fade">
          <span v-if="!collapsed && isActive('/org/dashboard')" class="ml-auto w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
        </Transition>
      </RouterLink>

      <!-- Submissions -->
      <RouterLink to="/org/submissions"
        :class="[
          'flex items-center gap-3 px-2.5 py-2.5 rounded-xl transition-all duration-150',
          isActive('/org/submissions')
            ? 'bg-white/15 text-white'
            : 'text-white/60 hover:bg-white/10 hover:text-white'
        ]">
        <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
        <Transition name="fade">
          <span v-if="!collapsed" class="text-sm font-medium truncate">Submissions</span>
        </Transition>
        <Transition name="fade">
          <span v-if="!collapsed && isActive('/org/submissions')" class="ml-auto w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
        </Transition>
      </RouterLink>

      <!-- Staff -->
      <RouterLink v-if="canViewStaff" to="/org/staff"
        :class="[
          'flex items-center gap-3 px-2.5 py-2.5 rounded-xl transition-all duration-150',
          isActive('/org/staff')
            ? 'bg-white/15 text-white'
            : 'text-white/60 hover:bg-white/10 hover:text-white'
        ]">
        <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
        </svg>
        <Transition name="fade">
          <span v-if="!collapsed" class="text-sm font-medium truncate">Staff</span>
        </Transition>
        <Transition name="fade">
          <span v-if="!collapsed && isActive('/org/staff')" class="ml-auto w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
        </Transition>
      </RouterLink>
      <span v-else
        title="You don't have permission to view staff"
        class="flex items-center gap-3 px-2.5 py-2.5 rounded-xl text-white/25 cursor-not-allowed select-none">
        <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
        </svg>
        <Transition name="fade">
          <span v-if="!collapsed" class="text-sm font-medium truncate">Staff</span>
        </Transition>
      </span>

      <!-- Roles -->
      <RouterLink v-if="canManageRoles" to="/org/roles"
        :class="[
          'flex items-center gap-3 px-2.5 py-2.5 rounded-xl transition-all duration-150',
          isActive('/org/roles')
            ? 'bg-white/15 text-white'
            : 'text-white/60 hover:bg-white/10 hover:text-white'
        ]">
        <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <Transition name="fade">
          <span v-if="!collapsed" class="text-sm font-medium truncate">Roles</span>
        </Transition>
        <Transition name="fade">
          <span v-if="!collapsed && isActive('/org/roles')" class="ml-auto w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
        </Transition>
      </RouterLink>
      <span v-else
        title="You don't have permission to manage roles"
        class="flex items-center gap-3 px-2.5 py-2.5 rounded-xl text-white/25 cursor-not-allowed select-none">
        <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <Transition name="fade">
          <span v-if="!collapsed" class="text-sm font-medium truncate">Roles</span>
        </Transition>
      </span>

      <!-- Map -->
      <RouterLink to="/org/map"
        :class="[
          'flex items-center gap-3 px-2.5 py-2.5 rounded-xl transition-all duration-150',
          isActive('/org/map')
            ? 'bg-white/15 text-white'
            : 'text-white/60 hover:bg-white/10 hover:text-white'
        ]">
        <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
        </svg>
        <Transition name="fade">
          <span v-if="!collapsed" class="text-sm font-medium truncate">Map</span>
        </Transition>
        <Transition name="fade">
          <span v-if="!collapsed && isActive('/org/map')" class="ml-auto w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
        </Transition>
      </RouterLink>

      <!-- Branches -->
      <RouterLink to="/org/branches"
        :class="[
          'flex items-center gap-3 px-2.5 py-2.5 rounded-xl transition-all duration-150',
          isActive('/org/branches')
            ? 'bg-white/15 text-white'
            : 'text-white/60 hover:bg-white/10 hover:text-white'
        ]">
        <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
        </svg>
        <Transition name="fade">
          <span v-if="!collapsed" class="text-sm font-medium truncate">Branches</span>
        </Transition>
        <Transition name="fade">
          <span v-if="!collapsed && isActive('/org/branches')" class="ml-auto w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
        </Transition>
      </RouterLink>

      <!-- AI Reports -->
      <RouterLink v-if="canViewStats" to="/org/reports"
        :class="[
          'flex items-center gap-3 px-2.5 py-2.5 rounded-xl transition-all duration-150',
          isActive('/org/reports')
            ? 'bg-white/15 text-white'
            : 'text-white/60 hover:bg-white/10 hover:text-white'
        ]">
        <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
        </svg>
        <Transition name="fade">
          <span v-if="!collapsed" class="text-sm font-medium truncate">AI Reports</span>
        </Transition>
        <Transition name="fade">
          <span v-if="!collapsed && isActive('/org/reports')" class="ml-auto w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
        </Transition>
      </RouterLink>

      <!-- QR Code -->
      <RouterLink to="/org/qrcode"
        :class="[
          'flex items-center gap-3 px-2.5 py-2.5 rounded-xl transition-all duration-150',
          isActive('/org/qrcode')
            ? 'bg-white/15 text-white'
            : 'text-white/60 hover:bg-white/10 hover:text-white'
        ]">
        <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z"/>
        </svg>
        <Transition name="fade">
          <span v-if="!collapsed" class="text-sm font-medium truncate">QR Code</span>
        </Transition>
        <Transition name="fade">
          <span v-if="!collapsed && isActive('/org/qrcode')" class="ml-auto w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
        </Transition>
      </RouterLink>
    </nav>

    <!-- Footer: public site link -->
    <div class="border-t border-white/10 p-2 shrink-0">
      <RouterLink to="/"
        class="flex items-center gap-3 px-2.5 py-2.5 rounded-xl text-white/40 hover:bg-white/10 hover:text-white transition-all duration-150">
        <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
        </svg>
        <Transition name="fade">
          <span v-if="!collapsed" class="text-sm font-medium">Public Site</span>
        </Transition>
      </RouterLink>
    </div>
  </aside>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
