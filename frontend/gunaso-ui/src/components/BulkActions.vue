<script setup>
defineProps({
  selectedCount: { type: Number, default: 0 },
})

defineEmits(['change-status', 'export-csv', 'deselect-all'])
</script>

<template>
  <Transition name="slide-up">
    <div v-if="selectedCount > 0"
      class="fixed bottom-6 left-1/2 -translate-x-1/2 z-30 bg-secondary dark:bg-gray-800 text-white rounded-2xl shadow-2xl px-5 py-3 flex items-center gap-3 border border-white/10">
      <span class="text-sm font-bold">{{ selectedCount }} selected</span>
      <div class="w-px h-5 bg-white/20" />
      <button
        @click="$emit('change-status')"
        class="text-sm font-medium hover:text-primary transition-colors px-2 py-1 rounded-lg hover:bg-white/10">
        Change Status
      </button>
      <button
        @click="$emit('export-csv')"
        class="text-sm font-medium hover:text-primary transition-colors px-2 py-1 rounded-lg hover:bg-white/10">
        Export CSV
      </button>
      <button
        @click="$emit('deselect-all')"
        class="ml-1 p-1.5 text-white/50 hover:text-white transition-colors rounded-lg hover:bg-white/10">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>
    </div>
  </Transition>
</template>

<style scoped>
.slide-up-enter-active, .slide-up-leave-active { transition: all 0.2s ease; }
.slide-up-enter-from, .slide-up-leave-to { transform: translate(-50%, 16px); opacity: 0; }
.slide-up-enter-to, .slide-up-leave-from { transform: translate(-50%, 0); opacity: 1; }
</style>
