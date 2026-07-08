import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'
import './assets/main.css'

const app = createApp(App)
app.use(createPinia())

// Restore the session (httpOnly refresh cookie → in-memory access token)
// before the router mounts, so guards see the correct auth state.
const authStore = useAuthStore()
authStore.init().finally(() => {
  app.use(router)
  app.mount('#app')
})
