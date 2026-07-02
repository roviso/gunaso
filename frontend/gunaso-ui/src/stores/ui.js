import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUIStore = defineStore('ui', () => {
  const darkMode = ref(localStorage.getItem('gunaso_dark') === 'true')
  const globalLoading = ref(false)
  const toasts = ref([])

  function applyDarkMode() {
    if (darkMode.value) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  function toggleDarkMode() {
    darkMode.value = !darkMode.value
    localStorage.setItem('gunaso_dark', String(darkMode.value))
    applyDarkMode()
  }

  function addToast(toast) {
    const id = Math.random().toString(36).slice(2)
    toasts.value.push({ id, ...toast })
    setTimeout(() => removeToast(id), toast.duration || 4500)
    return id
  }

  function removeToast(id) {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  function showSuccess(message) { addToast({ type: 'success', message }) }
  function showError(message) { addToast({ type: 'error', message, duration: 6000 }) }
  function showInfo(message) { addToast({ type: 'info', message }) }
  function showWarning(message) { addToast({ type: 'warning', message, duration: 5000 }) }

  return {
    darkMode, globalLoading, toasts,
    applyDarkMode, toggleDarkMode,
    addToast, removeToast,
    showSuccess, showError, showInfo, showWarning
  }
})
