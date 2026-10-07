<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const ref_ = ref('')

function track() {
  const value = ref_.value.trim().toUpperCase()
  if (value) router.push({ name: 'Track', params: { ref: value } })
}
</script>

<template>
  <div class="bg-app-bg dark:bg-gray-900 min-h-[calc(100vh-4rem)] flex items-center">
    <div class="page-container max-w-xl text-center py-20">
      <p class="font-display text-[7rem] leading-none font-extrabold text-secondary/10 dark:text-white/10 select-none" aria-hidden="true">404</p>
      <h1 class="font-display text-3xl font-extrabold text-secondary dark:text-white -mt-6 mb-3">This page went unanswered.</h1>
      <p class="text-gray-600 dark:text-gray-300 mb-8">The link may be old or mistyped. Here’s where you might have been heading:</p>
      <div class="flex flex-wrap justify-center gap-3 mb-10">
        <RouterLink to="/" class="btn-secondary">Home</RouterLink>
        <RouterLink to="/submit" class="btn-primary">File a gunaso</RouterLink>
        <RouterLink to="/organizations" class="btn-secondary">Organizations</RouterLink>
      </div>
      <form class="card p-4 flex gap-2 max-w-md mx-auto" @submit.prevent="track">
        <label for="nf-ref" class="sr-only">Reference number</label>
        <input id="nf-ref" v-model="ref_" class="input-base !py-2.5 font-mono uppercase" placeholder="GUN-2026-12345" />
        <button class="btn-primary !py-2.5 !px-5 shrink-0">Track</button>
      </form>
    </div>
  </div>
</template>
