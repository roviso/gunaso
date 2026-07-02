<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import AppNavbar from '@/components/AppNavbar.vue'
import AppFooter from '@/components/AppFooter.vue'
import ToastNotification from '@/components/ToastNotification.vue'

const authStore = useAuthStore()
const uiStore = useUIStore()

onMounted(async () => {
  uiStore.applyDarkMode()
  if (authStore.isAuthenticated) {
    await authStore.fetchMe()
  }
})
</script>

<template>
  <div class="min-h-screen flex flex-col font-sans">
    <AppNavbar />
    <main class="flex-1">
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>
    <AppFooter />
    <ToastNotification />
  </div>
</template>

<style>
.page-enter-active,
.page-leave-active {
  transition: opacity 0.15s ease;
}
.page-enter-from,
.page-leave-to {
  opacity: 0;
}
</style>
