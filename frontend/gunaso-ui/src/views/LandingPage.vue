<script setup>
import { onMounted } from 'vue'
import { useOrganizationStore } from '@/stores/organization'
import OrganizationCard from '@/components/OrganizationCard.vue'

const orgStore = useOrganizationStore()

const valueProps = [
  {
    title: 'No account needed',
    description: 'Submit in under 2 minutes — anonymously if you prefer. Your identity is never shown to organizations.',
    icon: 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z'
  },
  {
    title: 'A reference you can trust',
    description: 'Every submission gets a unique GUN- number. Track its status any time, from any device.',
    icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4'
  },
  {
    title: 'Tamper-proof timeline',
    description: 'Status changes are recorded in an append-only audit trail organizations can never edit or erase.',
    icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z'
  },
]

const steps = [
  {
    title: 'Find the organization',
    description: 'Search our directory of registered government bodies, telecoms, banks, and more.',
    icon: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z'
  },
  {
    title: 'Submit your complaint',
    description: 'Describe the issue, set a priority, and attach evidence — with or without an account.',
    icon: 'M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z'
  },
  {
    title: 'Track every step',
    description: 'Follow your unique reference number through a transparent status timeline until resolution.',
    icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z'
  },
]

// Illustrative example of the tracking timeline (clearly labeled as an example in the UI).
const demoTimeline = [
  { status: 'Submitted', note: 'Complaint filed with reference GUN-2026-XXXXX', color: 'bg-amber-400', time: 'Day 0' },
  { status: 'Acknowledged', note: 'Organization confirms receipt and assigns a reviewer', color: 'bg-cyan-400', time: 'Day 1' },
  { status: 'In Review', note: 'Issue is investigated; staff notes appear on your timeline', color: 'bg-blue-400', time: 'Day 3' },
  { status: 'Resolved', note: 'Outcome recorded — permanently, for everyone to see', color: 'bg-green-400', time: 'Day 6' },
]

onMounted(() => orgStore.fetchOrganizations({ limit: 6 }))
</script>

<template>
  <div>
    <!-- ===== HERO ===== -->
    <section class="relative bg-gradient-to-br from-secondary via-[#16294a] to-secondary-900 text-white overflow-hidden">
      <div class="pointer-events-none absolute top-0 right-0 w-[36rem] h-[36rem] bg-primary/15 rounded-full -translate-y-1/2 translate-x-1/3 blur-3xl" />
      <div class="pointer-events-none absolute bottom-0 left-10 w-72 h-72 bg-accent/15 rounded-full translate-y-1/2 blur-3xl" />
      <div class="pointer-events-none absolute inset-0 opacity-[0.04]"
        style="background-image: radial-gradient(currentColor 1px, transparent 1px); background-size: 28px 28px;" />

      <div class="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-28">
        <div class="grid lg:grid-cols-[1.2fr,1fr] gap-12 items-center">
          <div class="stagger">
            <div class="inline-flex items-center bg-primary/20 border border-primary/30 rounded-full px-4 py-1.5 mb-6 backdrop-blur-sm">
              <span class="w-2 h-2 bg-primary rounded-full mr-2 animate-pulse-dot flex-shrink-0" />
              <span class="text-sm font-medium text-primary-200">Nepal's Civic Grievance Platform</span>
            </div>

            <h1 class="font-display text-4xl sm:text-5xl lg:text-6xl font-bold leading-[1.05] mb-6 tracking-tight">
              Your voice,<br />
              <span class="text-primary">on the record.</span>
            </h1>

            <p class="text-lg sm:text-xl text-blue-100 mb-3 max-w-2xl leading-relaxed">
              Submit complaints and feedback to organizations across Nepal. Track resolution
              progress and hold institutions accountable — transparently.
            </p>
            <p class="text-base text-blue-300/80 italic mb-10">"आफ्नो आवाज उठाउनुस्" — Raise your voice.</p>

            <div class="flex flex-wrap gap-3">
              <RouterLink to="/submit"
                class="inline-flex items-center gap-2 bg-primary hover:bg-primary-600 active:scale-[0.98] text-white font-bold px-8 py-4 rounded-2xl shadow-glow transition-all duration-200 text-base">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4"/>
                </svg>
                Submit a Complaint
              </RouterLink>
              <RouterLink to="/track"
                class="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 active:scale-[0.98] border border-white/25 text-white font-semibold px-8 py-4 rounded-2xl transition-all duration-200 text-base backdrop-blur-sm">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                </svg>
                Track Your Complaint
              </RouterLink>
            </div>
          </div>

          <!-- Hero visual: the tracking timeline -->
          <div class="hidden lg:block animate-scale-in" style="animation-delay: 0.3s">
            <div class="rounded-3xl bg-white/[0.06] border border-white/10 backdrop-blur-sm p-6 shadow-2xl animate-float-slow">
              <div class="flex items-center justify-between mb-5">
                <span class="text-xs font-mono text-blue-200 bg-white/10 px-2.5 py-1 rounded-lg">GUN-2026-XXXXX</span>
                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-green-400/20 text-green-300 border border-green-400/30">
                  <span class="w-1.5 h-1.5 rounded-full bg-green-400" />
                  Resolved
                </span>
              </div>
              <div class="space-y-0">
                <div v-for="(item, i) in demoTimeline" :key="i" class="flex gap-3.5">
                  <div class="flex flex-col items-center">
                    <span :class="['w-2.5 h-2.5 rounded-full shrink-0 mt-1.5', item.color]" />
                    <span v-if="i < demoTimeline.length - 1" class="w-px flex-1 bg-white/15 my-1" />
                  </div>
                  <div class="pb-5">
                    <p class="text-sm font-semibold text-white leading-none mb-1">{{ item.status }}
                      <span class="text-[10px] text-blue-300/60 font-normal ml-1.5">{{ item.time }}</span>
                    </p>
                    <p class="text-xs text-blue-200/70 leading-relaxed">{{ item.note }}</p>
                  </div>
                </div>
              </div>
              <p class="text-[10px] text-blue-300/50 text-right">Example timeline</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== VALUE PROPS ===== -->
    <section class="bg-white dark:bg-gray-800 border-b border-gray-100 dark:border-gray-700">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div v-for="(prop, i) in valueProps" :key="i" class="flex items-start gap-4">
            <div class="w-11 h-11 rounded-xl bg-primary/10 dark:bg-primary/15 flex items-center justify-center shrink-0">
              <svg class="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" :d="prop.icon"/>
              </svg>
            </div>
            <div>
              <h3 class="font-display font-semibold text-secondary dark:text-white text-sm mb-1">{{ prop.title }}</h3>
              <p class="text-gray-500 dark:text-gray-400 text-sm leading-relaxed">{{ prop.description }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== FEATURED ORGS ===== -->
    <section class="py-16 bg-app-bg dark:bg-gray-900">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-end justify-between mb-8">
          <div>
            <h2 class="section-title">Featured Organizations</h2>
            <p class="text-gray-500 dark:text-gray-400 text-sm mt-1">Click any card to view details and submit feedback</p>
          </div>
          <RouterLink to="/organizations" class="text-primary font-semibold hover:underline text-sm flex items-center gap-1 shrink-0">
            View all
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
            </svg>
          </RouterLink>
        </div>

        <div v-if="orgStore.loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          <div v-for="i in 6" :key="i" class="card p-5 space-y-3">
            <div class="skeleton w-12 h-12 rounded-xl" />
            <div class="skeleton h-4 w-3/4" />
            <div class="skeleton h-3 w-full" />
            <div class="skeleton h-3 w-1/2" />
          </div>
        </div>
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          <OrganizationCard v-for="org in orgStore.organizations.slice(0, 6)" :key="org.id" :organization="org" />
        </div>
      </div>
    </section>

    <!-- ===== HOW IT WORKS ===== -->
    <section class="py-16 bg-white dark:bg-gray-800">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-12">
          <h2 class="section-title">How It Works</h2>
          <p class="text-gray-500 dark:text-gray-400 mt-2 text-sm">Three simple steps to make your voice heard</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
          <div v-for="(step, i) in steps" :key="i" class="relative text-center group">
            <div class="absolute -top-2 left-1/2 -translate-x-1/2 w-6 h-6 rounded-full bg-primary text-white text-xs font-bold flex items-center justify-center z-10 shadow-md">
              {{ i + 1 }}
            </div>
            <div class="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-primary/[0.08] dark:bg-primary/15 group-hover:bg-primary/15 dark:group-hover:bg-primary/25 group-hover:scale-105 transition-all duration-200 ease-spring mb-5">
              <svg class="w-8 h-8 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" :d="step.icon"/>
              </svg>
            </div>
            <h3 class="font-display font-bold text-secondary dark:text-white text-base mb-2">{{ step.title }}</h3>
            <p class="text-gray-500 dark:text-gray-400 text-sm leading-relaxed">{{ step.description }}</p>

            <div v-if="i < 2" class="hidden md:block absolute top-10 -right-5 text-gray-300 dark:text-gray-600">
              <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5l7 7-7 7"/>
              </svg>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== CTA BANNER ===== -->
    <section class="relative py-20 bg-gradient-to-r from-primary to-primary-700 overflow-hidden">
      <div class="pointer-events-none absolute inset-0 opacity-[0.06]"
        style="background-image: radial-gradient(white 1px, transparent 1px); background-size: 24px 24px;" />
      <div class="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <h2 class="font-display text-3xl sm:text-4xl font-bold text-white mb-4 tracking-tight">Ready to be heard?</h2>
        <p class="text-primary-100 mb-8 text-lg">It takes two minutes to file a complaint — and every step after that is on the record.</p>
        <div class="flex flex-wrap justify-center gap-4">
          <RouterLink to="/submit"
            class="bg-white text-primary font-bold px-8 py-4 rounded-2xl hover:bg-gray-50 active:scale-[0.98] transition-all duration-200 shadow-xl">
            Submit a Complaint
          </RouterLink>
          <RouterLink to="/register"
            class="border-2 border-white text-white font-semibold px-8 py-4 rounded-2xl hover:bg-white/10 active:scale-[0.98] transition-all duration-200">
            Create Free Account
          </RouterLink>
        </div>
      </div>
    </section>
  </div>
</template>
