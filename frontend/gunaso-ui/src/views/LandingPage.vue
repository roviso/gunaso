<script setup>
import { ref, onMounted } from 'vue'
import { useOrganizationStore } from '@/stores/organization'
import OrganizationCard from '@/components/OrganizationCard.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const orgStore = useOrganizationStore()

const stats = ref({ total_submissions: 6041, organizations: 48, resolved: 4320 })

const steps = [
  { icon: '🏢', title: 'Find Organization', description: 'Search our directory of registered government bodies, telecoms, banks, and more.' },
  { icon: '📝', title: 'Submit Complaint', description: 'Fill in your complaint or feedback with relevant details, priority, and attachments.' },
  { icon: '📍', title: 'Track Progress', description: 'Get a unique reference number and track every status update in real time.' },
]

const recentResolved = ref([
  { title: 'Billing dispute resolved — full refund processed', org: 'Nepal Telecom', category: 'Billing' },
  { title: 'Power outage complaint addressed within 48 hours', org: 'Nepal Electricity Authority', category: 'Service' },
  { title: 'Mobile network coverage improved in Bhaktapur area', org: 'Ncell', category: 'Coverage' },
  { title: 'Bank account freeze issue lifted after escalation', org: 'Nabil Bank', category: 'Account' },
  { title: 'Hospital appointment scheduling process improved', org: 'Bir Hospital', category: 'Service' },
])

onMounted(() => orgStore.fetchOrganizations({ limit: 6 }))
</script>

<template>
  <div>
    <!-- ===== HERO ===== -->
    <section class="relative bg-gradient-to-br from-secondary via-[#1a2e4a] to-[#0f1f38] text-white overflow-hidden">
      <div class="absolute top-0 right-0 w-96 h-96 bg-primary/15 rounded-full -translate-y-1/2 translate-x-1/2 blur-3xl pointer-events-none" />
      <div class="absolute bottom-0 left-10 w-72 h-72 bg-accent/15 rounded-full translate-y-1/2 blur-3xl pointer-events-none" />

      <div class="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-32">
        <div class="max-w-3xl">
          <div class="inline-flex items-center bg-primary/20 border border-primary/30 rounded-full px-4 py-1.5 mb-6 backdrop-blur-sm">
            <span class="w-2 h-2 bg-primary rounded-full mr-2 animate-pulse flex-shrink-0" />
            <span class="text-sm font-medium text-primary-200">Nepal's Civic Grievance Platform</span>
          </div>

          <h1 class="text-4xl sm:text-5xl lg:text-6xl font-extrabold leading-tight mb-6 tracking-tight">
            Your Voice<br />
            <span class="text-primary">Matters.</span>
          </h1>

          <p class="text-lg sm:text-xl text-blue-100 mb-3 max-w-2xl leading-relaxed">
            Submit complaints and feedback to organizations across Nepal. Track resolution progress and hold institutions accountable — transparently.
          </p>
          <p class="text-base text-blue-300/80 italic mb-10">"आफ्नो आवाज उठाउनुस्" — Raise your voice.</p>

          <div class="flex flex-wrap gap-3">
            <RouterLink to="/submit"
              class="inline-flex items-center gap-2 bg-primary hover:bg-primary-600 text-white font-bold px-8 py-4 rounded-2xl shadow-xl shadow-primary/25 hover:shadow-primary/40 transition-all duration-200 text-base">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4"/>
              </svg>
              Submit a Complaint
            </RouterLink>
            <RouterLink to="/track"
              class="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 border border-white/25 text-white font-semibold px-8 py-4 rounded-2xl transition-all duration-200 text-base backdrop-blur-sm">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>
              </svg>
              Track Your Complaint
            </RouterLink>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== STATS BAR ===== -->
    <section class="bg-white dark:bg-gray-800 border-b border-gray-100 dark:border-gray-700 shadow-sm">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5">
        <div class="grid grid-cols-3 divide-x divide-gray-200 dark:divide-gray-700 text-center">
          <div class="px-4 py-2">
            <div class="text-3xl font-extrabold text-secondary dark:text-white">{{ stats.total_submissions.toLocaleString() }}</div>
            <div class="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-0.5">Total Submissions</div>
          </div>
          <div class="px-4 py-2">
            <div class="text-3xl font-extrabold text-secondary dark:text-white">{{ stats.organizations }}</div>
            <div class="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-0.5">Organizations</div>
          </div>
          <div class="px-4 py-2">
            <div class="text-3xl font-extrabold text-green-600">{{ stats.resolved.toLocaleString() }}</div>
            <div class="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-0.5">Issues Resolved</div>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== FEATURED ORGS ===== -->
    <section class="py-16 bg-app-bg dark:bg-gray-900">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-end justify-between mb-8">
          <div>
            <h2 class="text-2xl font-extrabold text-secondary dark:text-white">Featured Organizations</h2>
            <p class="text-gray-500 dark:text-gray-400 text-sm mt-1">Click any card to view details and submit feedback</p>
          </div>
          <RouterLink to="/organizations" class="text-primary font-semibold hover:underline text-sm flex items-center gap-1 shrink-0">
            View all
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
            </svg>
          </RouterLink>
        </div>

        <LoadingSpinner v-if="orgStore.loading" />
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          <OrganizationCard v-for="org in orgStore.organizations.slice(0, 6)" :key="org.id" :organization="org" />
        </div>
      </div>
    </section>

    <!-- ===== HOW IT WORKS ===== -->
    <section class="py-16 bg-white dark:bg-gray-800">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-12">
          <h2 class="text-2xl font-extrabold text-secondary dark:text-white">How It Works</h2>
          <p class="text-gray-500 dark:text-gray-400 mt-2 text-sm">Three simple steps to make your voice heard</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
          <div v-for="(step, i) in steps" :key="i" class="relative text-center group">
            <!-- Number -->
            <div class="absolute -top-2 left-1/2 -translate-x-1/2 w-6 h-6 rounded-full bg-primary text-white text-xs font-bold flex items-center justify-center z-10 shadow-md">
              {{ i + 1 }}
            </div>
            <div class="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-primary/8 dark:bg-primary/15 group-hover:bg-primary/15 dark:group-hover:bg-primary/25 transition-colors mb-5 text-4xl pt-3">
              {{ step.icon }}
            </div>
            <h3 class="font-bold text-secondary dark:text-white text-base mb-2">{{ step.title }}</h3>
            <p class="text-gray-500 dark:text-gray-400 text-sm leading-relaxed">{{ step.description }}</p>

            <!-- Arrow -->
            <div v-if="i < 2" class="hidden md:block absolute top-10 -right-5 text-gray-300 dark:text-gray-600">
              <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5l7 7-7 7"/>
              </svg>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== RECENT RESOLVED ===== -->
    <section class="py-16 bg-app-bg dark:bg-gray-900">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-end justify-between mb-8">
          <div>
            <h2 class="text-2xl font-extrabold text-secondary dark:text-white">Recently Resolved</h2>
            <p class="text-gray-500 dark:text-gray-400 text-sm mt-1">Anonymized submissions that were successfully resolved</p>
          </div>
        </div>

        <div class="max-w-3xl space-y-2.5">
          <div v-for="(item, i) in recentResolved" :key="i"
            class="flex items-center gap-4 card p-4 hover:shadow-md transition-shadow">
            <div class="w-9 h-9 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center shrink-0">
              <svg class="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
              </svg>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-900 dark:text-white line-clamp-1">{{ item.title }}</p>
              <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{{ item.org }} · {{ item.category }}</p>
            </div>
            <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 shrink-0">
              <span class="w-1.5 h-1.5 rounded-full bg-green-500" />
              Resolved
            </span>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== CTA BANNER ===== -->
    <section class="py-16 bg-gradient-to-r from-primary to-primary-700">
      <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <h2 class="text-3xl font-extrabold text-white mb-4">Ready to Submit Your Complaint?</h2>
        <p class="text-primary-100 mb-8 text-lg">Join thousands of citizens who have already used Gunaso to resolve their issues.</p>
        <div class="flex flex-wrap justify-center gap-4">
          <RouterLink to="/submit"
            class="bg-white text-primary font-bold px-8 py-4 rounded-2xl hover:bg-gray-50 transition-colors shadow-xl">
            Submit a Complaint
          </RouterLink>
          <RouterLink to="/register"
            class="border-2 border-white text-white font-semibold px-8 py-4 rounded-2xl hover:bg-white/10 transition-colors">
            Create Free Account
          </RouterLink>
        </div>
      </div>
    </section>
  </div>
</template>
