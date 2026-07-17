<script setup>
import { ref, computed } from 'vue'

// Display mode (readonly): renders a fractional average (e.g. 4.3) via a
// clipped amber overlay. Input mode: 5 clickable stars with hover preview.
const props = defineProps({
  modelValue: { type: Number, default: null },
  readonly: { type: Boolean, default: false },
  size: { type: String, default: 'md' }, // sm | md | lg
})

const emit = defineEmits(['update:modelValue'])

const hovered = ref(0)

const sizeClass = computed(() => ({ sm: 'w-3.5 h-3.5', md: 'w-5 h-5', lg: 'w-7 h-7' }[props.size] || 'w-5 h-5'))
const fillPercent = computed(() => Math.max(0, Math.min(100, ((props.modelValue || 0) / 5) * 100)))
const shownScore = computed(() => hovered.value || props.modelValue || 0)

const STAR_PATH = 'M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.363-1.118l-2.8-2.034c-.784-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z'

function select(score) {
  if (!props.readonly) emit('update:modelValue', score)
}
</script>

<template>
  <!-- Readonly: fractional fill -->
  <div v-if="readonly" class="relative inline-flex" :aria-label="`Rated ${modelValue ?? 0} out of 5`" role="img">
    <div class="flex text-gray-300 dark:text-gray-600">
      <svg v-for="n in 5" :key="`bg-${n}`" :class="sizeClass" viewBox="0 0 20 20" fill="currentColor">
        <path :d="STAR_PATH"/>
      </svg>
    </div>
    <div class="absolute inset-0 flex overflow-hidden text-amber-400" :style="{ width: `${fillPercent}%` }">
      <svg v-for="n in 5" :key="`fg-${n}`" :class="[sizeClass, 'shrink-0']" viewBox="0 0 20 20" fill="currentColor">
        <path :d="STAR_PATH"/>
      </svg>
    </div>
  </div>

  <!-- Interactive: click to rate, hover to preview -->
  <div v-else class="inline-flex" @mouseleave="hovered = 0">
    <button v-for="n in 5" :key="n" type="button"
      @click="select(n)" @mouseenter="hovered = n"
      :aria-label="`Rate ${n} out of 5`"
      class="p-0.5 transition-transform duration-100 hover:scale-110 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 rounded">
      <svg :class="[sizeClass, n <= shownScore ? 'text-amber-400' : 'text-gray-300 dark:text-gray-600']"
        viewBox="0 0 20 20" fill="currentColor">
        <path :d="STAR_PATH"/>
      </svg>
    </button>
  </div>
</template>
