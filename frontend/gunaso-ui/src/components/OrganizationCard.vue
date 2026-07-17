<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import StarRating from '@/components/StarRating.vue'

const props = defineProps({ organization: { type: Object, required: true } })
const router = useRouter()

const categoryColor = computed(() => {
  const map = {
    Telecom:    'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300',
    Government: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    Bank:       'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
    Hospital:   'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300',
  }
  return map[props.organization.category] || 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
})

const initial = computed(() => props.organization.name?.[0]?.toUpperCase() || 'O')
const bgColors = ['bg-red-500', 'bg-blue-500', 'bg-violet-500', 'bg-emerald-500', 'bg-orange-500', 'bg-cyan-500']
const logoBg = computed(() => bgColors[props.organization.id % bgColors.length])

function goToDetail() {
  router.push(`/organizations/${props.organization.slug}`)
}

function goToSubmit(e) {
  e.stopPropagation()
  router.push({ name: 'Submit', query: { org: props.organization.slug } })
}
</script>

<template>
  <div @click="goToDetail"
    class="card p-5 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 cursor-pointer flex flex-col gap-4">
    <!-- Header -->
    <div class="flex items-center gap-3">
      <div :class="['w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold text-lg shrink-0', logoBg]">
        {{ initial }}
      </div>
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-1.5">
          <h3 class="font-bold text-gray-900 dark:text-white text-sm truncate">{{ organization.name }}</h3>
          <svg v-if="organization.verified" class="w-4 h-4 text-blue-500 shrink-0" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
          </svg>
        </div>
        <span :class="['inline-block text-xs font-medium px-2 py-0.5 rounded-md mt-0.5', categoryColor]">
          {{ organization.category }}
        </span>
      </div>
    </div>

    <!-- Rating (only when the org shares it publicly and has ratings) -->
    <div v-if="organization.average_rating != null" class="flex items-center gap-1.5 -mt-1">
      <StarRating :model-value="organization.average_rating" readonly size="sm" />
      <span class="text-xs font-semibold text-gray-700 dark:text-gray-200">{{ organization.average_rating }}</span>
      <span class="text-xs text-gray-400">({{ organization.rating_count }})</span>
    </div>

    <!-- Description -->
    <p class="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 -mt-1">{{ organization.description }}</p>

    <!-- Stats -->
    <div class="grid grid-cols-2 gap-2">
      <div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-2.5 text-center">
        <p class="text-base font-bold text-secondary dark:text-white">{{ organization.submission_count?.toLocaleString() }}</p>
        <p class="text-xs text-gray-500 dark:text-gray-400">Submissions</p>
      </div>
      <div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-2.5 text-center">
        <p :class="['text-base font-bold', organization.resolved_percent >= 80 ? 'text-green-600' : organization.resolved_percent >= 60 ? 'text-amber-600' : 'text-red-500']">
          {{ organization.resolved_percent }}%
        </p>
        <p class="text-xs text-gray-500 dark:text-gray-400">Resolved</p>
      </div>
    </div>

    <!-- CTA -->
    <button @click="goToSubmit"
      class="w-full py-2 text-sm font-semibold text-primary border border-primary rounded-xl hover:bg-primary hover:text-white transition-all duration-200">
      Submit Feedback
    </button>
  </div>
</template>
