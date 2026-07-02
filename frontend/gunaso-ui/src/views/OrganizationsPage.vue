<script setup>
import { ref, computed, onMounted } from 'vue'
import { useOrganizationStore } from '@/stores/organization'
import OrganizationCard from '@/components/OrganizationCard.vue'
import SearchInput from '@/components/SearchInput.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const orgStore = useOrganizationStore()
const search = ref('')
const activeCategory = ref('All')

const categories = ['All', 'Government', 'Telecom', 'Bank', 'Hospital', 'Education', 'Transport', 'Other']

const filtered = computed(() => {
  let list = orgStore.organizations
  if (activeCategory.value !== 'All') {
    list = list.filter((o) => o.category === activeCategory.value)
  }
  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    list = list.filter((o) => o.name.toLowerCase().includes(q) || o.description?.toLowerCase().includes(q) || o.category?.toLowerCase().includes(q))
  }
  return list
})

onMounted(() => orgStore.fetchOrganizations())
</script>

<template>
  <div class="bg-app-bg dark:bg-gray-900 min-h-screen">
    <!-- Hero -->
    <div class="bg-gradient-to-br from-secondary to-[#0f1f38] text-white py-12">
      <div class="page-container">
        <h1 class="text-3xl sm:text-4xl font-extrabold mb-2">Organizations</h1>
        <p class="text-blue-200 text-base">Browse registered organizations and submit your complaint or feedback.</p>
        <div class="mt-6 max-w-xl">
          <SearchInput v-model="search" placeholder="Search organizations by name or category..." />
        </div>
      </div>
    </div>

    <div class="page-container py-8">
      <!-- Category tabs -->
      <div class="flex gap-2 overflow-x-auto pb-2 mb-8 scrollbar-hide">
        <button v-for="cat in categories" :key="cat"
          @click="activeCategory = cat"
          :class="['px-4 py-2 rounded-xl text-sm font-semibold whitespace-nowrap transition-all duration-150 shrink-0',
            activeCategory === cat
              ? 'bg-secondary dark:bg-white text-white dark:text-secondary shadow-sm'
              : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:border-secondary dark:hover:border-gray-500']">
          {{ cat }}
        </button>
      </div>

      <LoadingSpinner v-if="orgStore.loading" />

      <template v-else>
        <!-- Result count -->
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-5">
          Showing <span class="font-semibold text-gray-900 dark:text-white">{{ filtered.length }}</span> organizations
          <span v-if="activeCategory !== 'All'"> in <span class="font-semibold">{{ activeCategory }}</span></span>
          <span v-if="search"> matching "<span class="font-semibold">{{ search }}</span>"</span>
        </p>

        <!-- Grid -->
        <div v-if="filtered.length" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          <OrganizationCard v-for="org in filtered" :key="org.id" :organization="org" />
        </div>

        <!-- Empty state -->
        <div v-else class="text-center py-16">
          <svg class="w-14 h-14 text-gray-300 dark:text-gray-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
          </svg>
          <p class="text-gray-500 dark:text-gray-400 font-medium">No organizations found</p>
          <p class="text-gray-400 dark:text-gray-500 text-sm mt-1">Try adjusting your search or filter.</p>
          <button @click="search = ''; activeCategory = 'All'" class="mt-4 text-primary text-sm font-medium hover:underline">
            Clear filters
          </button>
        </div>
      </template>
    </div>
  </div>
</template>
