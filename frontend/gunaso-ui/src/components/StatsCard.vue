<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  sub: { type: String, default: '' },
  color: { type: String, default: 'primary' },
  icon: { type: String, default: '' }
})
</script>

<template>
  <div class="card p-5">
    <div class="flex items-start justify-between">
      <div>
        <p class="text-sm font-medium text-gray-500 dark:text-gray-400">{{ label }}</p>
        <p :class="['text-3xl font-extrabold mt-1',
          color === 'green' ? 'text-green-600' :
          color === 'blue' ? 'text-blue-600' :
          color === 'orange' ? 'text-orange-500' :
          'text-secondary dark:text-white']">
          {{ value }}
        </p>
        <p v-if="sub" class="text-xs text-gray-400 dark:text-gray-500 mt-1">{{ sub }}</p>
      </div>
      <div v-if="icon" :class="['w-11 h-11 rounded-xl flex items-center justify-center text-xl',
        color === 'green' ? 'bg-green-50 dark:bg-green-900/20' :
        color === 'blue' ? 'bg-blue-50 dark:bg-blue-900/20' :
        color === 'orange' ? 'bg-orange-50 dark:bg-orange-900/20' :
        'bg-primary/10 dark:bg-primary/20']">
        {{ icon }}
      </div>
    </div>
  </div>
</template>
