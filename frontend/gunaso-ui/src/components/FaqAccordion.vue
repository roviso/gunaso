<script setup>
// Native <details>/<summary>: keyboard- and screen-reader-accessible for free,
// and the answers stay in the DOM for search engines.
defineProps({
  items: { type: Array, required: true },
})
</script>

<template>
  <div class="divide-y divide-gray-100 dark:divide-gray-700/70 card overflow-hidden">
    <details v-for="(item, i) in items" :key="i" class="group">
      <summary
        class="flex items-center justify-between gap-4 px-5 sm:px-6 py-4 cursor-pointer list-none select-none hover:bg-gray-50/70 dark:hover:bg-gray-700/30 transition-colors">
        <span class="font-semibold text-secondary dark:text-white text-[15px]">{{ item.q }}</span>
        <span class="w-7 h-7 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center shrink-0 transition-transform duration-200 group-open:rotate-45">
          <svg class="w-3.5 h-3.5 text-gray-500 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-width="2.5" d="M12 5v14M5 12h14"/>
          </svg>
        </span>
      </summary>
      <p class="px-5 sm:px-6 pb-5 -mt-1 text-sm leading-relaxed text-gray-600 dark:text-gray-300 max-w-3xl">{{ item.a }}</p>
    </details>
  </div>
</template>

<style scoped>
summary::-webkit-details-marker { display: none; }
</style>
