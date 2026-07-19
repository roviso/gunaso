<script setup>
import { ref, computed, onMounted } from 'vue'
import { organizationsAPI } from '@/api/organizations'
import { apiErrorMessage } from '@/api/index'
import { useUIStore } from '@/stores/ui'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

// Self-contained (local state, not the org store) so several instances can
// render at once — the branch QR gallery on OrgQRCodePage renders one per
// branch. When `branchId` is set, fetches that branch's own QR (the submit
// URL carries ?branch=<code> so the organization can trace the gunaso back
// to it); otherwise fetches the org-wide QR.
const props = defineProps({
  slug: { type: String, required: true },
  orgName: { type: String, default: '' },
  branchId: { type: [Number, String], default: null },
  branchName: { type: String, default: '' },
  compact: { type: Boolean, default: false },
})

const uiStore = useUIStore()
const loading = ref(true)
const error = ref(null)
const qr = ref(null)

const submitUrl = computed(() => qr.value?.url || '')

const qrImageSrc = computed(() => qr.value?.qr_code || null)

const fileLabel = computed(() => props.branchId ? `${props.slug}-${props.branchName || props.branchId}` : props.slug)

async function load() {
  loading.value = true
  error.value = null
  try {
    const { data } = props.branchId
      ? await organizationsAPI.getBranchQRCode(props.slug, props.branchId)
      : await organizationsAPI.getQRCode(props.slug)
    qr.value = data
  } catch (err) {
    error.value = apiErrorMessage(err, 'Could not load QR code.')
  } finally {
    loading.value = false
  }
}

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
  link.download = `${fileLabel.value}-qrcode.png`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

function printQR() {
  window.print()
}

onMounted(load)
</script>

<template>
  <div class="text-center">
    <LoadingSpinner v-if="loading" :size="compact ? 'sm' : undefined" />

    <div v-else-if="error" :class="['card', compact ? 'p-4' : 'p-8 max-w-sm mx-auto']">
      <p class="text-sm text-red-500 dark:text-red-400">{{ error }}</p>
    </div>

    <div v-else-if="qrImageSrc" :class="compact ? 'space-y-3' : 'space-y-6 max-w-sm mx-auto'">
      <!-- QR image -->
      <div :class="['card inline-block', compact ? 'p-4' : 'p-8']">
        <img :src="qrImageSrc" :alt="`QR code for ${branchName || orgName || slug}`"
          :class="compact ? 'w-32 h-32 mx-auto' : 'w-52 h-52 mx-auto'" />
      </div>

      <!-- Target URL -->
      <div v-if="!compact" class="text-left card p-4">
        <p class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">Submission URL</p>
        <a :href="submitUrl" target="_blank"
          class="text-sm text-primary hover:underline break-all font-mono">{{ submitUrl }}</a>
      </div>

      <!-- Actions -->
      <div :class="['flex flex-wrap justify-center gap-3', compact ? 'gap-2' : '']">
        <button @click="downloadQR" :class="compact ? 'btn-primary text-xs px-3 py-1.5' : 'btn-primary text-sm px-5 py-2.5'">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
          </svg>
          {{ compact ? 'Download' : 'Download PNG' }}
        </button>
        <button @click="copyLink" :class="compact ? 'btn-secondary text-xs px-3 py-1.5' : 'btn-secondary text-sm px-5 py-2.5'">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"/>
          </svg>
          Copy Link
        </button>
        <button v-if="!compact" @click="printQR" class="btn-secondary text-sm px-5 py-2.5">
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
