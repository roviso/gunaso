<script setup>
import { computed, onMounted } from 'vue'
import { useOrganizationStore } from '@/stores/organization'
import { useUIStore } from '@/stores/ui'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const props = defineProps({
  slug: { type: String, required: true },
  orgName: { type: String, default: '' },
})

const orgStore = useOrganizationStore()
const uiStore = useUIStore()

const submitUrl = computed(() => `${window.location.origin}/submit/${props.slug}`)

// The API returns {qr_code: 'data:image/png;base64,...', url, org_name, org_slug};
// `url` is the QR's target link, NOT an image — never use it as the img src.
const qrImageSrc = computed(() => {
  const qr = orgStore.qrCode
  if (!qr) return null
  if (qr.qr_code) return qr.qr_code
  if (qr.image) return qr.image
  if (qr.base64) return `data:image/png;base64,${qr.base64}`
  if (typeof qr === 'string') return qr
  return null
})

async function copyLink() {
  try {
    await navigator.clipboard.writeText(submitUrl.value)
    uiStore.showSuccess('Link copied to clipboard!')
  } catch {
    uiStore.showError('Could not copy to clipboard.')
  }
}

function downloadQR() {
  const src = qrImageSrc.value
  if (!src) return
  const link = document.createElement('a')
  link.href = src
  link.download = `${props.slug}-qrcode.png`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

function printQR() {
  window.print()
}

onMounted(() => orgStore.fetchQRCode(props.slug))
</script>

<template>
  <div class="text-center">
    <LoadingSpinner v-if="orgStore.qrLoading" />

    <div v-else-if="orgStore.qrError" class="card p-8 max-w-sm mx-auto">
      <div class="w-12 h-12 rounded-xl bg-red-50 dark:bg-red-900/20 flex items-center justify-center mx-auto mb-4">
        <svg class="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
      </div>
      <p class="font-semibold text-gray-800 dark:text-white mb-1">QR Code Unavailable</p>
      <p class="text-sm text-gray-500 dark:text-gray-400">{{ orgStore.qrError }}</p>
      <p class="text-xs text-gray-400 dark:text-gray-500 mt-3">
        The QR code endpoint may not yet be enabled on your backend.
      </p>
    </div>

    <div v-else-if="qrImageSrc" class="space-y-6 max-w-sm mx-auto">
      <!-- QR image -->
      <div class="card p-8 inline-block">
        <img :src="qrImageSrc" :alt="`QR code for ${orgName || slug}`" class="w-52 h-52 mx-auto" />
      </div>

      <!-- Target URL -->
      <div class="text-left card p-4">
        <p class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">Submission URL</p>
        <a :href="submitUrl" target="_blank"
          class="text-sm text-primary hover:underline break-all font-mono">{{ submitUrl }}</a>
      </div>

      <!-- Actions -->
      <div class="flex flex-wrap justify-center gap-3">
        <button @click="downloadQR" class="btn-primary text-sm px-5 py-2.5">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
          </svg>
          Download PNG
        </button>
        <button @click="copyLink" class="btn-secondary text-sm px-5 py-2.5">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"/>
          </svg>
          Copy Link
        </button>
        <button @click="printQR" class="btn-secondary text-sm px-5 py-2.5">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/>
          </svg>
          Print
        </button>
      </div>
    </div>

    <div v-else class="text-sm text-gray-400 dark:text-gray-500 py-10">
      No QR code data returned.
    </div>
  </div>
</template>
