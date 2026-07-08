<script setup>
import { computed } from 'vue'
import { useOrganizationStore } from '@/stores/organization'
import QRCodeDisplay from '@/components/QRCodeDisplay.vue'

const orgStore = useOrganizationStore()

const slug = computed(() => orgStore.currentOrg?.slug)
const orgName = computed(() => orgStore.currentOrg?.name || '')
const submitUrl = computed(() => slug.value ? `${window.location.origin}/submit/${slug.value}` : '')
</script>

<template>
  <div class="p-6 max-w-2xl mx-auto space-y-6">
    <!-- Header -->
    <div>
      <h1 class="text-xl font-extrabold text-secondary dark:text-white">QR Code</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
        Share your QR code so citizens can submit feedback directly.
      </p>
    </div>

    <!-- Info card -->
    <div class="card p-5 bg-blue-50 dark:bg-blue-900/15 border-blue-100 dark:border-blue-800">
      <div class="flex items-start gap-3">
        <div class="w-9 h-9 rounded-xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center shrink-0 mt-0.5">
          <svg class="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        </div>
        <div>
          <p class="text-sm font-semibold text-blue-800 dark:text-blue-200 mb-1">How to use your QR code</p>
          <p class="text-sm text-blue-700 dark:text-blue-300 leading-relaxed">
            Display this QR code in your office, website, or social media. When citizens scan it,
            they'll be taken directly to a pre-filled feedback form for
            <strong>{{ orgName || 'your organization' }}</strong> — no searching required.
          </p>
        </div>
      </div>
    </div>

    <!-- QR code display -->
    <div v-if="slug">
      <QRCodeDisplay :slug="slug" :org-name="orgName" />
    </div>
    <div v-else class="card p-10 text-center">
      <p class="text-sm text-gray-500 dark:text-gray-400">Organization not loaded yet. Please wait…</p>
    </div>

    <!-- Pre-filled submit form preview link -->
    <div v-if="submitUrl" class="card p-5">
      <h3 class="text-sm font-bold text-gray-800 dark:text-white mb-2">Pre-filled Submit URL</h3>
      <p class="text-xs text-gray-500 dark:text-gray-400 mb-3">
        You can also share this link directly. It opens the submission form with your organization already selected.
      </p>
      <div class="flex items-center gap-2 bg-gray-50 dark:bg-gray-700/50 rounded-xl px-4 py-3">
        <a :href="submitUrl" target="_blank"
          class="flex-1 text-sm text-primary hover:underline break-all font-mono min-w-0 truncate">
          {{ submitUrl }}
        </a>
        <a :href="submitUrl" target="_blank"
          class="shrink-0 p-1.5 rounded-lg text-gray-400 hover:text-secondary dark:hover:text-white hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          title="Open in new tab">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
          </svg>
        </a>
      </div>
    </div>
  </div>
</template>
