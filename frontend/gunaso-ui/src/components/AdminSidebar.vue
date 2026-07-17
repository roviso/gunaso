<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

defineProps({
  collapsed: { type: Boolean, default: false }
})

defineEmits(['toggle'])

const route = useRoute()

function isActive(path) {
  return route.path === path || route.path.startsWith(path + '/')
}

const links = [
  {
    to: '/admin/overview', label: 'Overview',
    icon: 'M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z',
  },
  {
    to: '/admin/organizations', label: 'Organizations',
    icon: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2M19 21H5m0 0H3m8-16h.01M11 12h.01M11 16h.01M15 8h.01M15 12h.01M15 16h.01',
  },
  {
    to: '/admin/users', label: 'Users',
    icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z',
  },
  {
    to: '/admin/submissions', label: 'Submissions',
    icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  },
  {
    to: '/admin/audit-log', label: 'Audit Log',
    icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4',
  },
]
</script>

<template>
  <aside
    :class="[
      'flex flex-col bg-gray-950 text-white transition-all duration-300 shrink-0 z-20',
      collapsed ? 'w-16' : 'w-60'
    ]">
    <!-- Superadmin header -->
    <div class="h-14 flex items-center border-b border-white/10 px-3 shrink-0">
      <RouterLink to="/admin/overview" class="flex items-center gap-3 min-w-0">
        <div class="w-8 h-8 rounded-xl bg-amber-500 flex items-center justify-center text-gray-950 font-bold text-sm shrink-0">
          <svg class="w-4.5 h-4.5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2l8 3v6c0 5-3.4 9.4-8 11-4.6-1.6-8-6-8-11V5l8-3z"/>
          </svg>
        </div>
        <Transition name="fade">
          <div v-if="!collapsed" class="min-w-0 overflow-hidden">
            <p class="text-sm font-bold text-white truncate leading-tight">Gunaso</p>
            <p class="text-xs text-amber-400 font-semibold tracking-wide">SUPERADMIN</p>
          </div>
        </Transition>
      </RouterLink>
    </div>

    <!-- Nav links -->
    <nav class="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
      <RouterLink v-for="link in links" :key="link.to" :to="link.to"
        :class="[
          'flex items-center gap-3 px-2.5 py-2.5 rounded-xl transition-all duration-150',
          isActive(link.to)
            ? 'bg-white/15 text-white'
            : 'text-white/60 hover:bg-white/10 hover:text-white'
        ]">
        <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="link.icon"/>
        </svg>
        <Transition name="fade">
          <span v-if="!collapsed" class="text-sm font-medium truncate">{{ link.label }}</span>
        </Transition>
        <Transition name="fade">
          <span v-if="!collapsed && isActive(link.to)" class="ml-auto w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
        </Transition>
      </RouterLink>
    </nav>

    <!-- Footer: exit admin -->
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
