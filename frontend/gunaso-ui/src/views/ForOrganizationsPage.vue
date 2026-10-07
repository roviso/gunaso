<script setup>
import { organizationFaq } from '@/content/faq'
import FaqAccordion from '@/components/FaqAccordion.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const pains = [
  'A paper register nobody reads',
  'Complaints buried in Facebook comments',
  'Phone calls that end with “call again tomorrow”',
  'No idea which branch the problem is at',
]

const onboarding = [
  { title: 'Register', body: 'Create an account and tell us about your organization. Takes five minutes.' },
  { title: 'Get verified', body: 'Our team confirms you are who you say you are, then lists you publicly.' },
  { title: 'Add branches', body: 'Pin each office on the map and print its QR code for the counter.' },
  { title: 'Bring your team', body: 'Invite staff with exactly the permissions their role needs.' },
]
</script>

<template>
  <div>
    <!-- HERO -->
    <section class="relative overflow-hidden bg-secondary-900 text-white">
      <div class="pointer-events-none absolute -top-32 left-1/3 w-[40rem] h-[40rem] bg-primary/20 rounded-full blur-3xl" />
      <div class="pointer-events-none absolute inset-0 opacity-[0.045]"
        style="background-image: linear-gradient(currentColor 1px, transparent 1px), linear-gradient(90deg, currentColor 1px, transparent 1px); background-size: 44px 44px;" />
      <div class="relative page-container py-20 lg:py-28 text-center max-w-4xl">
        <p class="text-xs font-bold uppercase tracking-[0.25em] text-primary-200 mb-5">Gunaso for organizations</p>
        <h1 class="font-display text-4xl sm:text-6xl font-extrabold tracking-tight leading-[1.04] mb-6">
          Your citizens are already complaining.<br class="hidden sm:block" />
          <span class="text-primary">Now you can actually hear them.</span>
        </h1>
        <p class="text-lg sm:text-xl text-blue-100/90 max-w-2xl mx-auto leading-relaxed mb-10">
          One queue for every complaint, feedback and suggestion — tagged to the branch it came from,
          routed to the right person, and answered on a record that builds public trust.
        </p>
        <div class="flex flex-wrap justify-center gap-3">
          <RouterLink to="/org/register" class="inline-flex items-center gap-2 bg-primary hover:bg-primary-600 text-white font-bold px-8 py-4 rounded-2xl shadow-glow transition-all">
            Register your organization
          </RouterLink>
          <RouterLink :to="{ name: 'Contact', query: { topic: 'organization' } }" class="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 border border-white/25 text-white font-semibold px-8 py-4 rounded-2xl transition-all">
            Talk to us first
          </RouterLink>
        </div>
      </div>
    </section>

    <!-- PROBLEM -->
    <section class="py-20 bg-app-bg dark:bg-gray-900">
      <div class="page-container grid lg:grid-cols-2 gap-10 items-center">
        <div>
          <p class="text-xs font-bold uppercase tracking-[0.2em] text-primary mb-3">The problem</p>
          <h2 class="font-display text-3xl sm:text-4xl font-extrabold text-secondary dark:text-white tracking-tight mb-5">
            Complaints don’t disappear when you can’t see them.
          </h2>
          <p class="text-gray-600 dark:text-gray-300 leading-relaxed">
            They turn into bad reviews, viral posts and lost trust. The feedback that could fix your service
            is scattered across channels nobody owns.
          </p>
        </div>
        <ul class="grid sm:grid-cols-2 gap-3">
          <li v-for="p in pains" :key="p" class="card p-5 flex gap-3 items-start">
            <span class="w-7 h-7 rounded-full bg-red-50 dark:bg-red-900/30 text-red-500 flex items-center justify-center shrink-0">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12"/></svg>
            </span>
            <span class="text-sm font-medium text-gray-700 dark:text-gray-200">{{ p }}</span>
          </li>
        </ul>
      </div>
    </section>

    <!-- FEATURE 1: branches + QR + hotspots -->
    <section class="py-20 bg-white dark:bg-gray-800 border-y border-gray-100 dark:border-gray-700">
      <div class="page-container grid lg:grid-cols-2 gap-12 items-center">
        <div>
          <p class="text-xs font-bold uppercase tracking-[0.2em] text-primary mb-3">Every branch, accounted for</p>
          <h2 class="font-display text-3xl font-extrabold text-secondary dark:text-white tracking-tight mb-4">A QR code at every counter. A hotspot map in your dashboard.</h2>
          <p class="text-gray-600 dark:text-gray-300 leading-relaxed mb-5">
            Each branch gets its own QR code. A citizen scans it, writes their gunaso, and it lands tagged to that
            exact office. Your map shows where cases pile up, which ones are overdue, and what people are saying — live.
          </p>
          <ul class="space-y-2 text-sm text-gray-700 dark:text-gray-200">
            <li>✓ Printable QR codes per branch</li>
            <li>✓ Branch-by-branch volume, open and overdue counts</li>
            <li>✓ Branches appear on the public map so citizens find the right office</li>
          </ul>
        </div>
        <div class="relative rounded-3xl bg-gradient-to-br from-secondary/5 to-primary/5 dark:from-gray-700/40 dark:to-gray-700/10 p-6 sm:p-8" aria-hidden="true">
          <div class="relative h-72 rounded-2xl bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-700 overflow-hidden">
            <div class="absolute inset-0 opacity-[0.15]" style="background-image: radial-gradient(#1D3557 1.3px, transparent 1.3px); background-size: 16px 16px;" />
            <span v-for="(dot, i) in [
              { x: 22, y: 30, s: 58, c: 'bg-red-500', n: 14 }, { x: 60, y: 22, s: 40, c: 'bg-amber-400', n: 6 },
              { x: 45, y: 62, s: 48, c: 'bg-amber-400', n: 9 }, { x: 78, y: 58, s: 30, c: 'bg-green-500', n: 3 },
              { x: 15, y: 72, s: 26, c: 'bg-green-500', n: 2 },
            ]" :key="i" :class="['absolute rounded-full text-white font-extrabold flex items-center justify-center ring-4 ring-white dark:ring-gray-900 shadow-lg', dot.c]"
              :style="{ left: `${dot.x}%`, top: `${dot.y}%`, width: `${dot.s}px`, height: `${dot.s}px`, fontSize: '13px' }">
              {{ dot.n }}
            </span>
            <span class="absolute left-[22%] top-[30%] -translate-x-2 -translate-y-2 w-[74px] h-[74px] rounded-full bg-red-500/25 animate-ping" />
          </div>
          <div class="absolute -bottom-5 -left-3 sm:left-4 card !rounded-2xl p-3 flex items-center gap-3 shadow-card-hover">
            <div class="w-14 h-14 rounded-lg bg-white p-1 border border-gray-200">
              <svg viewBox="0 0 21 21" class="w-full h-full"><path fill="#111827" d="M0 0h7v7H0zm2 2v3h3V2zM14 0h7v7h-7zm2 2v3h3V2zM0 14h7v7H0zm2 2v3h3v-3zM9 0h2v2H9zm0 4h3v2H9zm-1 4h2v3H8zm4 0h2v2h-2zm4 0h2v2h-2zm2 3h3v2h-3zm-6 1h2v2h-2zm-4 1h3v2H8zm8 1h2v3h-2zm-5 2h3v2h-3zm6 2h2v2h-2zm-9 1h2v2H9z"/></svg>
            </div>
            <div class="text-xs">
              <p class="font-bold text-gray-900 dark:text-white">Baneshwor branch</p>
              <p class="text-gray-500 dark:text-gray-400">Scan to file a gunaso</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- FEATURE 2: team workflow -->
    <section class="py-20 bg-app-bg dark:bg-gray-900">
      <div class="page-container grid lg:grid-cols-2 gap-12 items-center">
        <div class="order-2 lg:order-1 card !rounded-3xl p-5 space-y-2.5" aria-hidden="true">
          <div class="flex gap-1.5 mb-2">
            <span class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-secondary text-white">Open</span>
            <span class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-300">⏰ Overdue 3</span>
            <span class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-200">💬 Waiting 2</span>
          </div>
          <div v-for="row in [
            { t: 'ATM at New Road swallowed my card', s: 'in_review', who: 'Anita K.', flag: 'Citizen waiting' },
            { t: 'Long queue, only one counter open', s: 'acknowledged', who: 'Unassigned', flag: 'Overdue' },
            { t: 'Staff was very helpful with my loan', s: 'resolved', who: 'Ramesh T.', flag: '' },
          ]" :key="row.t" class="flex items-center gap-3 p-3 rounded-xl bg-gray-50 dark:bg-gray-700/40">
            <div class="min-w-0 flex-1">
              <p class="text-sm font-semibold text-gray-800 dark:text-gray-100 truncate">{{ row.t }}</p>
              <p class="text-[11px] text-gray-500 dark:text-gray-400">→ {{ row.who }}
                <span v-if="row.flag" :class="['ml-1 px-1.5 rounded-full font-bold', row.flag === 'Overdue' ? 'bg-red-50 text-red-600' : 'bg-blue-50 text-blue-700']">{{ row.flag }}</span>
              </p>
            </div>
            <StatusBadge :status="row.s" />
          </div>
          <div class="p-3 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-dashed border-amber-300 dark:border-amber-700 text-xs text-amber-900 dark:text-amber-100">
            🔒 <b>Internal note:</b> Checked CCTV — card retained by machine, branch manager to return today.
          </div>
        </div>
        <div class="order-1 lg:order-2">
          <p class="text-xs font-bold uppercase tracking-[0.2em] text-primary mb-3">Built for teams</p>
          <h2 class="font-display text-3xl font-extrabold text-secondary dark:text-white tracking-tight mb-4">Nothing falls through the cracks.</h2>
          <p class="text-gray-600 dark:text-gray-300 leading-relaxed mb-5">
            Work queues for what’s open, overdue, unassigned or waiting on you. Assign cases, reply to citizens,
            and keep internal notes that never leave your team.
          </p>
          <ul class="space-y-2 text-sm text-gray-700 dark:text-gray-200">
            <li>✓ Custom roles — give each person exactly the access they need</li>
            <li>✓ Overdue flags when a response or resolution target is missed</li>
            <li>✓ Citizens are emailed automatically on every status change and reply</li>
            <li>✓ One-click CSV export of any view</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- FEATURE 3: AI + trust -->
    <section class="py-20 bg-white dark:bg-gray-800 border-y border-gray-100 dark:border-gray-700">
      <div class="page-container grid md:grid-cols-2 gap-5">
        <div class="rounded-3xl p-8 bg-violet-50 dark:bg-violet-900/15 border border-violet-100 dark:border-violet-800/50">
          <p class="text-xs font-bold uppercase tracking-[0.2em] text-violet-600 dark:text-violet-300 mb-3">AI assistance</p>
          <h3 class="font-display text-2xl font-extrabold text-secondary dark:text-white mb-3">Sort, summarise and reply faster.</h3>
          <p class="text-gray-600 dark:text-gray-300 text-sm leading-relaxed mb-5">
            Automatic categorisation, suggested replies in both Nepali and English (सुझाव), and period reports that
            surface recurring themes — without ever sending a citizen’s identity to the AI.
          </p>
          <div class="rounded-2xl bg-white dark:bg-gray-900 p-4 text-sm shadow-sm" aria-hidden="true">
            <p class="text-[11px] font-bold text-violet-600 uppercase tracking-wide mb-1.5">🤖 AI सुझाव</p>
            <p class="text-gray-700 dark:text-gray-200">तपाईंको कार्ड आज साँझसम्म शाखाबाट फिर्ता गरिनेछ।</p>
            <p class="text-gray-500 dark:text-gray-400 mt-1.5">Your card will be returned from the branch by this evening.</p>
          </div>
        </div>
        <div class="rounded-3xl p-8 bg-green-50 dark:bg-green-900/15 border border-green-100 dark:border-green-800/50">
          <p class="text-xs font-bold uppercase tracking-[0.2em] text-green-700 dark:text-green-300 mb-3">Public trust</p>
          <h3 class="font-display text-2xl font-extrabold text-secondary dark:text-white mb-3">Let your track record speak.</h3>
          <p class="text-gray-600 dark:text-gray-300 text-sm leading-relaxed mb-5">
            Your public profile shows how many cases you resolve, how fast, and how citizens rate the outcome.
            Showcase resolved cases you’re proud of. Organizations that listen, stand out.
          </p>
          <div class="grid grid-cols-3 gap-2 text-center" aria-hidden="true">
            <div class="rounded-2xl bg-white dark:bg-gray-900 p-3 shadow-sm"><p class="font-display text-2xl font-extrabold text-green-600">92%</p><p class="text-[10px] uppercase tracking-wide text-gray-400">resolved</p></div>
            <div class="rounded-2xl bg-white dark:bg-gray-900 p-3 shadow-sm"><p class="font-display text-2xl font-extrabold text-secondary dark:text-white">3.1d</p><p class="text-[10px] uppercase tracking-wide text-gray-400">to resolve</p></div>
            <div class="rounded-2xl bg-white dark:bg-gray-900 p-3 shadow-sm"><p class="font-display text-2xl font-extrabold text-amber-500">4.6★</p><p class="text-[10px] uppercase tracking-wide text-gray-400">rating</p></div>
          </div>
          <p class="text-[10px] text-gray-400 mt-2 text-right">Illustrative figures</p>
        </div>
      </div>
    </section>

    <!-- ONBOARDING -->
    <section class="py-20 bg-app-bg dark:bg-gray-900">
      <div class="page-container">
        <div class="text-center max-w-2xl mx-auto mb-12">
          <p class="text-xs font-bold uppercase tracking-[0.2em] text-primary mb-3">Getting started</p>
          <h2 class="font-display text-3xl sm:text-4xl font-extrabold text-secondary dark:text-white tracking-tight">Live in an afternoon.</h2>
        </div>
        <ol class="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <li v-for="(s, i) in onboarding" :key="s.title" class="card p-6">
            <span class="w-9 h-9 rounded-full bg-primary text-white font-bold flex items-center justify-center mb-4">{{ i + 1 }}</span>
            <h3 class="font-display font-bold text-secondary dark:text-white mb-1.5">{{ s.title }}</h3>
            <p class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">{{ s.body }}</p>
          </li>
        </ol>
      </div>
    </section>

    <!-- FAQ -->
    <section class="pb-20 bg-app-bg dark:bg-gray-900">
      <div class="page-container max-w-4xl">
        <h2 class="font-display text-2xl font-extrabold text-secondary dark:text-white mb-6">Questions organizations ask</h2>
        <FaqAccordion :items="organizationFaq" />
      </div>
    </section>

    <!-- CTA -->
    <section class="relative py-20 bg-secondary overflow-hidden">
      <div class="pointer-events-none absolute -right-24 -top-24 w-96 h-96 rounded-full bg-primary/30 blur-3xl" />
      <div class="relative page-container text-center max-w-3xl">
        <h2 class="font-display text-3xl sm:text-5xl font-extrabold text-white tracking-tight mb-4">Start listening.</h2>
        <p class="text-blue-100 text-lg mb-9">Register today — we’ll verify your organization and help you set up your first branches.</p>
        <div class="flex flex-wrap justify-center gap-3">
          <RouterLink to="/org/register" class="bg-primary hover:bg-primary-600 text-white font-bold px-8 py-4 rounded-2xl shadow-glow transition-all">Register your organization</RouterLink>
          <RouterLink :to="{ name: 'Contact', query: { topic: 'organization' } }" class="border border-white/30 text-white font-semibold px-8 py-4 rounded-2xl hover:bg-white/10 transition-all">Book a walkthrough</RouterLink>
        </div>
      </div>
    </section>
  </div>
</template>
