<script setup>
// The Gunaso mark: a speech bubble (a voice raised) closed by a tick (an
// answer given). Used by the navbar, footer and sidebars.
defineProps({
  size: { type: Number, default: 32 },
  withWordmark: { type: Boolean, default: true },
  inverted: { type: Boolean, default: false },
})
</script>

<template>
  <span class="inline-flex items-center gap-2">
    <svg :width="size" :height="size" viewBox="0 0 40 40" aria-hidden="true" class="shrink-0">
      <path d="M8 4h24a6 6 0 0 1 6 6v15a6 6 0 0 1-6 6H18l-8 6v-6H8a6 6 0 0 1-6-6V10a6 6 0 0 1 6-6z" fill="#E63946"/>
      <path d="M12.5 17.5l5 5 10-10" fill="none" stroke="#fff" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    <span v-if="withWordmark"
      :class="['font-display font-bold tracking-tight leading-none', inverted ? 'text-white' : 'text-secondary dark:text-white']"
      :style="{ fontSize: `${Math.round(size * 0.58)}px` }">
      Gunaso
    </span>
  </span>
</template>
