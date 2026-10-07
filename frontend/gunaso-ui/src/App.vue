<script setup>
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import { isNative } from '@/native'
import AppNavbar from '@/components/AppNavbar.vue'
import AppFooter from '@/components/AppFooter.vue'
import MobileTabBar from '@/components/MobileTabBar.vue'
import ToastNotification from '@/components/ToastNotification.vue'

const authStore = useAuthStore()
const uiStore = useUIStore()
const route = useRoute()

onMounted(async () => {
  uiStore.applyDarkMode()
  if (authStore.isAuthenticated) {
    await authStore.fetchMe()
  }
})
</script>

<template>
  <div :class="route.meta.fullPage ? 'h-screen overflow-hidden app-full' : 'min-h-screen flex flex-col font-sans'">
    <AppNavbar v-if="!route.meta.fullPage" />
    <main :class="route.meta.fullPage ? '' : ['flex-1', isNative && 'pb-24']">
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>
    <AppFooter v-if="!route.meta.fullPage && !isNative" />
    <MobileTabBar v-if="!route.meta.fullPage && isNative" />
    <ToastNotification v-if="!route.meta.fullPage" />
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
