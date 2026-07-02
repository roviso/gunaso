<script setup>
import { useUIStore } from '@/stores/ui'

const uiStore = useUIStore()

function toastClass(type) {
  return {
    success: 'bg-green-50 border-green-200 text-green-900 dark:bg-green-900/40 dark:border-green-700 dark:text-green-200',
    error:   'bg-red-50 border-red-200 text-red-900 dark:bg-red-900/40 dark:border-red-700 dark:text-red-200',
    warning: 'bg-amber-50 border-amber-200 text-amber-900 dark:bg-amber-900/40 dark:border-amber-700 dark:text-amber-200',
    info:    'bg-blue-50 border-blue-200 text-blue-900 dark:bg-blue-900/40 dark:border-blue-700 dark:text-blue-200',
  }[type] || 'bg-gray-50 border-gray-200 text-gray-900 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-200'
}

function iconClass(type) {
  return {
    success: 'text-green-600 dark:text-green-400',
    error:   'text-red-600 dark:text-red-400',
    warning: 'text-amber-600 dark:text-amber-400',
    info:    'text-blue-600 dark:text-blue-400',
  }[type] || 'text-gray-500'
}
</script>

<template>
  <div class="fixed bottom-5 right-5 z-[100] flex flex-col gap-2.5 pointer-events-none max-w-sm w-full">
    <TransitionGroup name="toast">
      <div v-for="toast in uiStore.toasts" :key="toast.id"
        :class="['pointer-events-auto flex items-start gap-3 px-4 py-3.5 rounded-2xl shadow-xl border backdrop-blur-sm', toastClass(toast.type)]">

        <!-- Icon -->
        <div :class="['mt-0.5 shrink-0', iconClass(toast.type)]">
          <svg v-if="toast.type === 'success'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <svg v-else-if="toast.type === 'error'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <svg v-else-if="toast.type === 'warning'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
          </svg>
          <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        </div>

        <p class="text-sm font-medium flex-1">{{ toast.message }}</p>

        <button @click="uiStore.removeToast(toast.id)"
          class="ml-1 shrink-0 opacity-50 hover:opacity-100 transition-opacity">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-active { transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
.toast-leave-active { transition: all 0.2s ease; }
.toast-enter-from  { opacity: 0; transform: translateX(110%) scale(0.95); }
.toast-leave-to    { opacity: 0; transform: translateX(110%) scale(0.95); }
.toast-move        { transition: transform 0.3s ease; }
</style>
