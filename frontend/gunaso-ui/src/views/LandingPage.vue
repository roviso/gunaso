<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOrganizationStore } from '@/stores/organization'
import { publicAPI } from '@/api/public'
import { citizenFaq } from '@/content/faq'
import { useCountUp } from '@/composables/useCountUp'
import OrganizationCard from '@/components/OrganizationCard.vue'
import FaqAccordion from '@/components/FaqAccordion.vue'
import LandingMapPreview from '@/components/LandingMapPreview.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const router = useRouter()
const orgStore = useOrganizationStore()

// ── Live, identity-free platform numbers (never faked: if there's nothing
// meaningful to show yet, the band shows product facts instead) ─────────────
const stats = ref(null)
const stories = ref([])
const mapSummary = ref(null)

const hasTraction = computed(() => (stats.value?.submissions || 0) >= 10)
const filed = useCountUp(() => (hasTraction.value ? stats.value.submissions : null))
const rate = useCountUp(() => (hasTraction.value ? stats.value.resolution_rate : null))
const orgCount = useCountUp(() => (hasTraction.value ? stats.value.organizations : null))
const avgDays = useCountUp(() => (hasTraction.value ? stats.value.avg_resolution_days : null))

// ── Quick track in the hero ─────────────────────────────────────────────────
const quickRef = ref('')
function quickTrack() {
  const value = quickRef.value.trim().toUpperCase()
  if (value) router.push({ name: 'Track', params: { ref: value } })
}

const steps = [
  {
    title: 'Find them',
    np: 'खोज्नुहोस्',
    description: 'Search the directory, pick an office on the map, or scan the QR code at the counter.',
    icon: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z',
  },
  {
    title: 'Tell them',
    np: 'भन्नुहोस्',
    description: 'Describe what happened in your own words — Nepali or English. Add a photo if it helps. Stay anonymous if you want.',
    icon: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z',
  },
  {
    title: 'Follow it through',
    np: 'पछ्याउनुहोस्',
    description: 'Get a reference and a private link. See every step, reply to them, and rate the outcome when it’s done.',
    icon: 'M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z',
  },
]

const pillars = [
  { title: 'Tamper-proof history', body: 'Every status change and reply is time-stamped on an append-only record. Nobody — not even the organization — can edit or delete it.', icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z' },
  { title: 'Anonymous by design', body: 'Choose anonymous and your identity never reaches the organization — not in dashboards, exports or emails.', icon: 'M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21' },
  { title: 'A private line back', body: 'Your private follow-up link lets you reply and rate the outcome — no account, no password, no identity required.', icon: 'M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z' },
  { title: 'Public track records', body: 'Resolution rates, response times and citizen ratings are public — the organizations that listen stand out.', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
  { title: 'Updates that find you', body: 'Leave an email and we’ll tell you the moment your gunaso moves — acknowledged, replied to, resolved.', icon: 'M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9' },
  { title: 'Verified organizations', body: 'Every organization is checked by the Gunaso team before it appears — you’re always talking to the real office.', icon: 'M5 13l4 4L19 7' },
]

const orgBenefits = [
  'Branch-specific QR codes and a hotspot map of where issues come from',
  'Work queues, staff roles, assignment and internal notes',
  'Overdue alerts before a citizen gives up on you',
  'AI categorisation and bilingual reply suggestions',
  'Spreadsheet exports and period reports for management',
]
const citizenBenefits = [
  'No account, no forms to print, no office visit',
  'Anonymous whenever you need it to be',
  'A reference number and private follow-up link',
  'Email updates the moment something changes',
]

function relative(d) {
  if (!d) return ''
  const days = Math.round((Date.now() - new Date(d).getTime()) / 86400000)
  if (days < 1) return 'today'
  if (days === 1) return 'yesterday'
  if (days < 30) return `${days} days ago`
  return new Date(d).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
}

onMounted(() => {
  orgStore.fetchOrganizations({ page_size: 6 })
  publicAPI.stats().then(({ data }) => { stats.value = data }).catch(() => { stats.value = null })
  publicAPI.stories().then(({ data }) => { stories.value = data }).catch(() => { stories.value = [] })
})
</script>

<template>
  <div>
    <!-- ═══════════════ HERO ═══════════════ -->
    <section class="relative overflow-hidden bg-gradient-to-br from-secondary via-[#16294a] to-secondary-900 text-white">
      <div class="pointer-events-none absolute -top-40 -right-32 w-[42rem] h-[42rem] bg-primary/20 rounded-full blur-3xl" />
      <div class="pointer-events-none absolute -bottom-40 -left-24 w-96 h-96 bg-accent/20 rounded-full blur-3xl" />
      <div class="pointer-events-none absolute inset-0 opacity-[0.045]"
        style="background-image: radial-gradient(currentColor 1px, transparent 1px); background-size: 28px 28px;" />

      <div class="relative page-container pt-14 pb-24 sm:pt-20 lg:pt-24 lg:pb-32">
        <div class="grid lg:grid-cols-[1.15fr,1fr] gap-14 items-center">
          <div class="stagger">
            <div class="inline-flex items-center bg-white/10 border border-white/15 rounded-full pl-2 pr-4 py-1.5 mb-7 backdrop-blur-sm">
              <span class="bg-primary text-white text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full mr-2.5">Free</span>
              <span class="text-sm font-medium text-blue-100">Nepal’s civic grievance platform</span>
            </div>

            <h1 class="font-display text-[2.7rem] leading-[1.02] sm:text-6xl lg:text-[4.4rem] font-extrabold tracking-tight mb-6">
              Every gunaso<br />
              deserves
              <span class="relative whitespace-nowrap text-primary">
                an answer.
                <svg class="absolute -bottom-2 left-0 w-full h-3 text-primary/60" viewBox="0 0 200 12" preserveAspectRatio="none" aria-hidden="true">
                  <path d="M2 9c40-6 110-8 196-3" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" class="origin-left animate-draw-line" style="animation-delay:.6s" />
                </svg>
              </span>
            </h1>

            <p class="text-lg sm:text-xl text-blue-100/90 mb-3 max-w-xl leading-relaxed">
              Tell any registered office, bank, hospital or ward what went wrong — in two minutes,
              anonymously if you want. Then watch them respond on a public record they can’t edit.
            </p>
            <p class="text-base text-blue-300/80 italic mb-9">“आफ्नो आवाज उठाउनुस्” — Raise your voice.</p>

            <div class="flex flex-wrap gap-3 mb-8">
              <RouterLink to="/submit"
                class="inline-flex items-center gap-2 bg-primary hover:bg-primary-600 active:scale-[0.98] text-white font-bold px-7 sm:px-8 py-4 rounded-2xl shadow-glow transition-all duration-200 text-base">
                File a gunaso
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 7l5 5m0 0l-5 5m5-5H6"/>
                </svg>
              </RouterLink>
              <RouterLink to="/map"
                class="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 active:scale-[0.98] border border-white/25 text-white font-semibold px-7 py-4 rounded-2xl transition-all duration-200 text-base backdrop-blur-sm">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
                </svg>
                Find an office near you
              </RouterLink>
            </div>

            <form class="max-w-md" @submit.prevent="quickTrack">
              <label for="hero-track" class="block text-xs font-semibold uppercase tracking-wider text-blue-300/80 mb-2">Already filed one?</label>
              <div class="flex gap-2 p-1.5 rounded-2xl bg-white/[0.07] border border-white/15 backdrop-blur-sm focus-within:border-white/35 transition-colors">
                <input id="hero-track" v-model="quickRef" type="text" placeholder="GUN-2026-12345" autocomplete="off" spellcheck="false"
                  class="flex-1 min-w-0 bg-transparent border-0 focus:ring-0 text-white placeholder-white/35 font-mono uppercase tracking-wider text-sm px-3" />
                <button type="submit" class="shrink-0 bg-white text-secondary font-bold text-sm px-5 py-2.5 rounded-xl hover:bg-blue-50 transition-colors">Track</button>
              </div>
            </form>

            <ul class="mt-7 flex flex-wrap gap-x-6 gap-y-2 text-sm text-blue-100/80">
              <li v-for="t in ['No account needed', 'Anonymous option', 'Free for citizens, always']" :key="t" class="inline-flex items-center gap-1.5">
                <svg class="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/></svg>
                {{ t }}
              </li>
            </ul>
          </div>

          <!-- Hero visual: an (illustrative) case, as the citizen sees it -->
          <div class="relative hidden lg:block animate-scale-in" style="animation-delay: .25s" aria-hidden="true">
            <div class="absolute -left-12 -top-7 z-20 rounded-2xl bg-white text-secondary shadow-2xl px-4 py-3 text-xs font-semibold flex items-center gap-2 animate-float-slow" style="animation-delay:1s">
              <span class="w-8 h-8 rounded-xl bg-secondary text-white flex items-center justify-center">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-width="2" d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h2v2h-2zM18 18h2v2h-2z"/></svg>
              </span>
              <span>Filed via QR at<br /><span class="text-gray-500 font-medium">Baneshwor branch</span></span>
            </div>

            <div class="relative rounded-[2rem] bg-white/[0.07] border border-white/10 backdrop-blur-md p-6 shadow-2xl">
              <div class="flex items-center justify-between mb-5">
                <span class="text-xs font-mono text-blue-200 bg-white/10 px-2.5 py-1 rounded-lg">GUN-2026-XXXXX</span>
                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-green-400/20 text-green-300 border border-green-400/30">
                  <span class="w-1.5 h-1.5 rounded-full bg-green-400" /> Resolved
                </span>
              </div>
              <p class="font-semibold text-white mb-5">Streetlight outside the ward office broken for 3 weeks</p>

              <div class="flex items-center gap-1.5 mb-6">
                <template v-for="(label, i) in ['Submitted', 'Acknowledged', 'In review', 'Resolved']" :key="label">
                  <div class="flex flex-col items-center gap-1.5 flex-1">
                    <span class="w-6 h-6 rounded-full bg-green-400 text-secondary-900 flex items-center justify-center">
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3.5" d="M5 13l4 4L19 7"/></svg>
                    </span>
                    <span class="text-[10px] text-blue-200/80">{{ label }}</span>
                  </div>
                  <span v-if="i < 3" class="h-0.5 flex-1 bg-green-400/60 -mt-5" />
                </template>
              </div>

              <div class="space-y-3">
                <div class="max-w-[85%] rounded-2xl rounded-tl-sm bg-white/10 px-4 py-2.5">
                  <p class="text-[10px] uppercase tracking-wider text-blue-300/70 font-semibold mb-0.5">Ward office · Day 1</p>
                  <p class="text-sm text-white/90">Thanks — our electrician will inspect it this week.</p>
                </div>
                <div class="max-w-[80%] ml-auto rounded-2xl rounded-tr-sm bg-primary/80 px-4 py-2.5">
                  <p class="text-[10px] uppercase tracking-wider text-white/70 font-semibold mb-0.5">You · Day 3</p>
                  <p class="text-sm text-white">The pole on the left side is also out.</p>
                </div>
                <div class="max-w-[85%] rounded-2xl rounded-tl-sm bg-white/10 px-4 py-2.5">
                  <p class="text-[10px] uppercase tracking-wider text-blue-300/70 font-semibold mb-0.5">Ward office · Day 4</p>
                  <p class="text-sm text-white/90">Both lights replaced. Please let us know if it happens again.</p>
                </div>
              </div>
              <p class="text-[10px] text-blue-300/50 text-right mt-4">Illustrative example</p>
            </div>

            <div class="absolute -right-6 -bottom-8 z-20 rounded-2xl bg-white text-secondary shadow-2xl px-4 py-3 animate-float-slow">
              <p class="text-amber-400 text-lg leading-none tracking-tight">★★★★★</p>
              <p class="text-xs font-semibold mt-1">“Fixed in 4 days.”</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══════════════ PROOF BAND ═══════════════ -->
    <section class="relative z-10 -mt-12">
      <div class="page-container">
        <div class="card !rounded-3xl shadow-card-hover grid grid-cols-2 lg:grid-cols-4 divide-y lg:divide-y-0 lg:divide-x divide-gray-100 dark:divide-gray-700 overflow-hidden">
          <template v-if="hasTraction">
            <div class="p-6 sm:p-7 text-center">
              <p class="font-display text-3xl sm:text-4xl font-extrabold text-secondary dark:text-white tabular-nums">{{ filed.toLocaleString() }}</p>
              <p class="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-1">gunaso on the record</p>
            </div>
            <div class="p-6 sm:p-7 text-center">
              <p class="font-display text-3xl sm:text-4xl font-extrabold text-green-600 tabular-nums">{{ rate }}%</p>
              <p class="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-1">resolved or closed</p>
            </div>
            <div class="p-6 sm:p-7 text-center">
              <p class="font-display text-3xl sm:text-4xl font-extrabold text-secondary dark:text-white tabular-nums">{{ orgCount }}</p>
              <p class="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-1">verified organizations</p>
            </div>
            <div class="p-6 sm:p-7 text-center">
              <p class="font-display text-3xl sm:text-4xl font-extrabold text-primary tabular-nums">{{ stats.avg_resolution_days != null ? avgDays : '—' }}</p>
              <p class="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-1">avg. days to resolve</p>
            </div>
          </template>
          <template v-else>
            <div v-for="fact in [
              { big: '2 min', small: 'to file a gunaso' },
              { big: '0', small: 'accounts or paperwork needed' },
              { big: '100%', small: 'anonymous, if you choose' },
              { big: '24/7', small: 'track from any device' },
            ]" :key="fact.small" class="p-6 sm:p-7 text-center">
              <p class="font-display text-3xl sm:text-4xl font-extrabold text-secondary dark:text-white">{{ fact.big }}</p>
              <p class="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-1">{{ fact.small }}</p>
            </div>
          </template>
        </div>
      </div>
    </section>

    <!-- ═══════════════ HOW IT WORKS ═══════════════ -->
    <section class="py-20 sm:py-24 bg-app-bg dark:bg-gray-900">
      <div class="page-container">
        <div class="max-w-2xl mb-12">
          <p class="text-xs font-bold uppercase tracking-[0.2em] text-primary mb-3">How it works</p>
          <h2 class="font-display text-3xl sm:text-4xl font-extrabold text-secondary dark:text-white tracking-tight">
            From “नसुनिने गुनासो” to a documented answer, in three steps.
          </h2>
        </div>
        <ol class="grid md:grid-cols-3 gap-5">
          <li v-for="(step, i) in steps" :key="step.title" class="card p-7 relative overflow-hidden group">
            <span class="absolute -right-3 -top-6 font-display text-[7rem] font-extrabold text-gray-100 dark:text-gray-700/50 leading-none select-none" aria-hidden="true">{{ i + 1 }}</span>
            <div class="relative">
              <div class="w-12 h-12 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mb-5 group-hover:scale-110 transition-transform duration-300 ease-spring">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" :d="step.icon"/></svg>
              </div>
              <h3 class="font-display text-xl font-bold text-secondary dark:text-white">{{ step.title }} <span class="text-sm font-medium text-gray-400">· {{ step.np }}</span></h3>
              <p class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed mt-2">{{ step.description }}</p>
            </div>
          </li>
        </ol>
        <div class="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3">
          <RouterLink to="/submit" class="btn-primary">File a gunaso now</RouterLink>
          <RouterLink to="/how-it-works" class="text-sm font-semibold text-secondary dark:text-white hover:text-primary">Read the full guide & FAQ →</RouterLink>
        </div>
      </div>
    </section>

    <!-- ═══════════════ TWO AUDIENCES ═══════════════ -->
    <section class="pb-20 sm:pb-24 bg-app-bg dark:bg-gray-900">
      <div class="page-container grid lg:grid-cols-2 gap-5">
        <div class="card !rounded-3xl p-8 sm:p-10 flex flex-col">
          <p class="text-xs font-bold uppercase tracking-[0.2em] text-primary mb-3">For citizens</p>
          <h3 class="font-display text-2xl sm:text-3xl font-extrabold text-secondary dark:text-white tracking-tight mb-5">Be heard without the runaround.</h3>
          <ul class="space-y-3 mb-8">
            <li v-for="b in citizenBenefits" :key="b" class="flex gap-3 text-gray-700 dark:text-gray-200">
              <svg class="w-5 h-5 text-green-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>
              {{ b }}
            </li>
          </ul>
          <div class="mt-auto flex flex-wrap gap-3">
            <RouterLink to="/submit" class="btn-primary">File a gunaso</RouterLink>
            <RouterLink to="/register" class="btn-secondary">Create free account</RouterLink>
          </div>
        </div>

        <div class="relative rounded-3xl p-8 sm:p-10 flex flex-col bg-secondary text-white overflow-hidden">
          <div class="pointer-events-none absolute -right-20 -bottom-20 w-72 h-72 rounded-full bg-primary/25 blur-3xl" />
          <p class="relative text-xs font-bold uppercase tracking-[0.2em] text-primary-200 mb-3">For organizations</p>
          <h3 class="relative font-display text-2xl sm:text-3xl font-extrabold tracking-tight mb-5">Turn complaints into your best service data.</h3>
          <ul class="relative space-y-3 mb-8">
            <li v-for="b in orgBenefits" :key="b" class="flex gap-3 text-blue-100">
              <svg class="w-5 h-5 text-primary-300 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>
              {{ b }}
            </li>
          </ul>
          <div class="relative mt-auto flex flex-wrap gap-3">
            <RouterLink to="/for-organizations" class="inline-flex items-center gap-2 bg-white text-secondary font-bold px-6 py-3 rounded-xl hover:bg-blue-50 transition-colors">See how it works</RouterLink>
            <RouterLink to="/org/register" class="inline-flex items-center gap-2 border border-white/30 text-white font-semibold px-6 py-3 rounded-xl hover:bg-white/10 transition-colors">Register your organization</RouterLink>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══════════════ MAP ═══════════════ -->
    <section class="py-20 sm:py-24 bg-white dark:bg-gray-800 border-y border-gray-100 dark:border-gray-700">
      <div class="page-container grid lg:grid-cols-[1fr,1.35fr] gap-10 items-center">
        <div>
          <p class="text-xs font-bold uppercase tracking-[0.2em] text-primary mb-3">The map</p>
          <h2 class="font-display text-3xl sm:text-4xl font-extrabold text-secondary dark:text-white tracking-tight mb-4">
            Find the exact office — then file right from the pin.
          </h2>
          <p class="text-gray-600 dark:text-gray-300 leading-relaxed mb-6">
            Head offices and branches, with their resolution rate and citizen rating on every pin.
            Tap <strong>Near me</strong> to see what’s closest, and your gunaso goes straight to that branch.
          </p>
          <p v-if="mapSummary?.organizations" class="text-sm text-gray-500 dark:text-gray-400 mb-6">
            {{ mapSummary.organizations }} organization{{ mapSummary.organizations === 1 ? '' : 's' }} · {{ mapSummary.points }} location{{ mapSummary.points === 1 ? '' : 's' }} mapped so far
          </p>
          <RouterLink to="/map" class="btn-primary">Open the map</RouterLink>
        </div>
        <div class="h-[360px] sm:h-[440px] shadow-card-hover rounded-3xl">
          <LandingMapPreview @loaded="mapSummary = $event" />
        </div>
      </div>
    </section>

    <!-- ═══════════════ PILLARS ═══════════════ -->
    <section class="py-20 sm:py-24 bg-app-bg dark:bg-gray-900">
      <div class="page-container">
        <div class="max-w-2xl mb-12">
          <p class="text-xs font-bold uppercase tracking-[0.2em] text-primary mb-3">Built for accountability</p>
          <h2 class="font-display text-3xl sm:text-4xl font-extrabold text-secondary dark:text-white tracking-tight">
            A complaint box that can’t be emptied into the bin.
          </h2>
        </div>
        <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          <div v-for="p in pillars" :key="p.title" class="card p-6">
            <div class="w-11 h-11 rounded-xl bg-secondary/[0.07] dark:bg-white/10 text-secondary dark:text-white flex items-center justify-center mb-4">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" :d="p.icon"/></svg>
            </div>
            <h3 class="font-display font-bold text-secondary dark:text-white mb-1.5">{{ p.title }}</h3>
            <p class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">{{ p.body }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══════════════ STORIES (real, org-showcased cases) ═══════════════ -->
    <section v-if="stories.length" class="pb-20 sm:pb-24 bg-app-bg dark:bg-gray-900">
      <div class="page-container">
        <div class="flex items-end justify-between gap-4 mb-8">
          <div>
            <p class="text-xs font-bold uppercase tracking-[0.2em] text-primary mb-3">On the record</p>
            <h2 class="font-display text-3xl font-extrabold text-secondary dark:text-white tracking-tight">Recently shared by organizations</h2>
          </div>
        </div>
        <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          <RouterLink v-for="s in stories" :key="s.reference_number" :to="{ name: 'Track', params: { ref: s.reference_number } }"
            class="card-interactive p-6 flex flex-col">
            <div class="flex items-center justify-between gap-2 mb-3">
              <StatusBadge :status="s.status" />
              <span class="text-xs text-gray-400">{{ relative(s.updated_at) }}</span>
            </div>
            <p class="font-semibold text-gray-900 dark:text-white leading-snug line-clamp-2">{{ s.title }}</p>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-2 line-clamp-3">{{ s.description }}</p>
            <p class="mt-auto pt-4 text-xs font-semibold text-accent">{{ s.organization_name }}</p>
          </RouterLink>
        </div>
      </div>
    </section>

    <!-- ═══════════════ ORGANIZATIONS ═══════════════ -->
    <section v-if="orgStore.loading || orgStore.organizations.length" class="py-20 sm:py-24 bg-white dark:bg-gray-800 border-y border-gray-100 dark:border-gray-700">
      <div class="page-container">
        <div class="flex items-end justify-between gap-4 mb-8">
          <div>
            <p class="text-xs font-bold uppercase tracking-[0.2em] text-primary mb-3">Directory</p>
            <h2 class="font-display text-3xl font-extrabold text-secondary dark:text-white tracking-tight">Organizations listening on Gunaso</h2>
          </div>
          <RouterLink to="/organizations" class="text-primary font-semibold hover:underline text-sm flex items-center gap-1 shrink-0">
            View all
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
          </RouterLink>
        </div>
        <div v-if="orgStore.loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          <div v-for="i in 3" :key="i" class="card p-5 space-y-3">
            <div class="skeleton w-12 h-12 rounded-xl" /><div class="skeleton h-4 w-3/4" /><div class="skeleton h-3 w-full" />
          </div>
        </div>
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          <OrganizationCard v-for="org in orgStore.organizations.slice(0, 6)" :key="org.id" :organization="org" />
        </div>
      </div>
    </section>

    <!-- ═══════════════ FAQ ═══════════════ -->
    <section class="py-20 sm:py-24 bg-app-bg dark:bg-gray-900">
      <div class="page-container grid lg:grid-cols-[1fr,1.6fr] gap-10">
        <div>
          <p class="text-xs font-bold uppercase tracking-[0.2em] text-primary mb-3">Questions</p>
          <h2 class="font-display text-3xl sm:text-4xl font-extrabold text-secondary dark:text-white tracking-tight mb-4">Before you file</h2>
          <p class="text-gray-600 dark:text-gray-300 mb-6">Straight answers about privacy, anonymity and what happens to your gunaso.</p>
          <RouterLink to="/how-it-works#faq" class="text-sm font-semibold text-primary hover:underline">All questions →</RouterLink>
        </div>
        <FaqAccordion :items="citizenFaq.slice(0, 4)" />
      </div>
    </section>

    <!-- ═══════════════ FINAL CTA ═══════════════ -->
    <section class="relative py-20 sm:py-24 bg-gradient-to-br from-primary to-primary-700 overflow-hidden">
      <div class="pointer-events-none absolute inset-0 opacity-[0.07]"
        style="background-image: radial-gradient(white 1px, transparent 1px); background-size: 24px 24px;" />
      <div class="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <h2 class="font-display text-3xl sm:text-5xl font-extrabold text-white mb-4 tracking-tight">Something went wrong? Say so.</h2>
        <p class="text-primary-100 mb-9 text-lg max-w-2xl mx-auto">Two minutes to file. A permanent record of every step after that. That’s how things get fixed.</p>
        <div class="flex flex-wrap justify-center gap-4">
          <RouterLink to="/submit" class="bg-white text-primary font-bold px-8 py-4 rounded-2xl hover:bg-gray-50 active:scale-[0.98] transition-all duration-200 shadow-xl">
            File a gunaso
          </RouterLink>
          <RouterLink to="/for-organizations" class="border-2 border-white/80 text-white font-semibold px-8 py-4 rounded-2xl hover:bg-white/10 active:scale-[0.98] transition-all duration-200">
            I represent an organization
          </RouterLink>
        </div>
      </div>
    </section>
  </div>
</template>
