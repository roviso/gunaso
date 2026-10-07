<script setup>
import { citizenFaq, organizationFaq } from '@/content/faq'
import FaqAccordion from '@/components/FaqAccordion.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const journey = [
  { title: 'Choose who to tell', body: 'Search the directory, find the office on the map, or scan the QR code at the counter — a QR code also tells them which branch you visited.' },
  { title: 'Describe what happened', body: 'One box, your own words, Nepali or English. Title, category, priority and a photo or document are optional extras.' },
  { title: 'Decide who you are', body: 'Leave your name and email to get updates — or switch on “anonymous” and the organization never learns who you are.' },
  { title: 'Keep your reference and private link', body: 'The GUN- reference shows anyone the status. The private link is yours alone: it lets you reply and rate the outcome.' },
  { title: 'Follow it to the end', body: 'Watch each step on the timeline, answer questions from the organization, and rate how they handled it once it’s resolved.' },
]

const statuses = [
  { s: 'submitted', meaning: 'Recorded and delivered to the organization. Waiting for them to acknowledge it.' },
  { s: 'acknowledged', meaning: 'The organization has seen it and accepted it for handling.' },
  { s: 'in_review', meaning: 'Someone is actively working on it. Replies and questions appear on the timeline.' },
  { s: 'escalated', meaning: 'Passed to a more senior team — usually because it’s serious or stuck.' },
  { s: 'resolved', meaning: 'The organization says it’s fixed. You can rate the outcome.' },
  { s: 'rejected', meaning: 'The organization decided not to act, and should explain why in a note.' },
  { s: 'closed', meaning: 'Final. The case is archived — file a new gunaso if the problem returns.' },
]

const visibility = [
  { what: 'What you wrote, category, photos', org: true, publicRef: true },
  { what: 'Status history and the organization’s replies', org: true, publicRef: true },
  { what: 'Your name (if not anonymous)', org: true, publicRef: true },
  { what: 'Your email and phone (if not anonymous)', org: 'Case handlers only', publicRef: false },
  { what: 'Anything identifying you, when anonymous', org: false, publicRef: false },
  { what: 'The organization’s internal notes', org: true, publicRef: false },
]
</script>

<template>
  <div class="bg-app-bg dark:bg-gray-900">
    <section class="bg-gradient-to-br from-secondary to-secondary-900 text-white">
      <div class="page-container py-16 sm:py-20 max-w-4xl">
        <p class="text-xs font-bold uppercase tracking-[0.2em] text-primary-200 mb-3">How it works</p>
        <h1 class="font-display text-4xl sm:text-5xl font-extrabold tracking-tight mb-4">From your first sentence to a documented answer.</h1>
        <p class="text-lg text-blue-100/90 max-w-2xl">Everything that happens to a gunaso on Gunaso — and exactly who can see what along the way.</p>
      </div>
    </section>

    <section class="page-container max-w-4xl py-16">
      <h2 class="font-display text-2xl sm:text-3xl font-extrabold text-secondary dark:text-white mb-8">Filing and following a gunaso</h2>
      <ol class="relative border-l-2 border-gray-200 dark:border-gray-700 ml-4 space-y-8">
        <li v-for="(step, i) in journey" :key="step.title" class="pl-8 relative">
          <span class="absolute -left-[17px] top-0 w-8 h-8 rounded-full bg-primary text-white text-sm font-bold flex items-center justify-center ring-4 ring-app-bg dark:ring-gray-900">{{ i + 1 }}</span>
          <h3 class="font-display font-bold text-lg text-secondary dark:text-white">{{ step.title }}</h3>
          <p class="text-gray-600 dark:text-gray-300 mt-1 leading-relaxed">{{ step.body }}</p>
        </li>
      </ol>
      <div class="mt-10 flex flex-wrap gap-3">
        <RouterLink to="/submit" class="btn-primary">File a gunaso</RouterLink>
        <RouterLink :to="{ name: 'Track' }" class="btn-secondary">Track one</RouterLink>
      </div>
    </section>

    <section class="bg-white dark:bg-gray-800 border-y border-gray-100 dark:border-gray-700">
      <div class="page-container max-w-4xl py-16">
        <h2 class="font-display text-2xl sm:text-3xl font-extrabold text-secondary dark:text-white mb-2">What each status means</h2>
        <p class="text-gray-600 dark:text-gray-300 mb-8">Organizations can only move a case forward along these steps, and every move is recorded permanently.</p>
        <dl class="divide-y divide-gray-100 dark:divide-gray-700">
          <div v-for="row in statuses" :key="row.s" class="py-4 grid sm:grid-cols-[160px,1fr] gap-2 items-start">
            <dt><StatusBadge :status="row.s" /></dt>
            <dd class="text-sm text-gray-700 dark:text-gray-200 leading-relaxed">{{ row.meaning }}</dd>
          </div>
        </dl>
      </div>
    </section>

    <section class="page-container max-w-4xl py-16">
      <h2 class="font-display text-2xl sm:text-3xl font-extrabold text-secondary dark:text-white mb-2">Who can see what</h2>
      <p class="text-gray-600 dark:text-gray-300 mb-6">
        Anyone with your reference number can see the public status page. Only you, with your private link or account, can reply.
      </p>
      <div class="card overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/50">
              <th class="px-5 py-3 font-semibold">Information</th>
              <th class="px-5 py-3 font-semibold">The organization</th>
              <th class="px-5 py-3 font-semibold">Public status page</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
            <tr v-for="row in visibility" :key="row.what">
              <td class="px-5 py-3.5 text-gray-800 dark:text-gray-100 font-medium">{{ row.what }}</td>
              <td class="px-5 py-3.5">
                <span v-if="row.org === true" class="text-green-600 font-semibold">Yes</span>
                <span v-else-if="row.org === false" class="text-gray-400 font-semibold">Never</span>
                <span v-else class="text-amber-600 font-semibold">{{ row.org }}</span>
              </td>
              <td class="px-5 py-3.5">
                <span v-if="row.publicRef" class="text-green-600 font-semibold">Yes</span>
                <span v-else class="text-gray-400 font-semibold">No</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="text-xs text-gray-500 dark:text-gray-400 mt-3">
        Gunaso platform staff can see identity on anonymous cases, only to handle abuse and legal obligations.
        See the <RouterLink to="/privacy" class="text-primary hover:underline">privacy policy</RouterLink>.
      </p>
    </section>

    <section id="faq" class="page-container max-w-4xl pb-20 scroll-mt-24">
      <h2 class="font-display text-2xl sm:text-3xl font-extrabold text-secondary dark:text-white mb-6">Frequently asked questions</h2>
      <h3 class="text-xs font-bold uppercase tracking-[0.2em] text-primary mb-3">For citizens</h3>
      <FaqAccordion :items="citizenFaq" />
      <h3 class="text-xs font-bold uppercase tracking-[0.2em] text-primary mt-10 mb-3">For organizations</h3>
      <FaqAccordion :items="organizationFaq" />
      <p class="text-sm text-gray-600 dark:text-gray-300 mt-8">
        Still stuck? <RouterLink to="/contact" class="text-primary font-semibold hover:underline">Contact us</RouterLink>.
      </p>
    </section>
  </div>
</template>
