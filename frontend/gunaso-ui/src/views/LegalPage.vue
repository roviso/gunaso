<script setup>
import { computed } from 'vue'

// Plain-language policies. They describe how the platform actually behaves
// today (see CLAUDE.md) — update them whenever data handling changes.
const props = defineProps({
  page: { type: String, required: true }, // 'privacy' | 'terms' | 'child-safety'
})

const UPDATED = '30 September 2026'

const docs = {
  privacy: {
    title: 'Privacy policy',
    intro: 'Gunaso exists so people can hold organizations accountable without putting themselves at risk. This page explains, in plain language, what we collect, why, and who can see it.',
    sections: [
      {
        h: 'What we collect',
        p: [
          'What you write in a gunaso: its type, description, optional title, category and priority, and any file you attach.',
          'Contact details you choose to give: your name, email and phone. These are optional when you submit anonymously — and when you do, the form does not send them.',
          'If you create an account: your name, email, username, optional phone and a securely hashed password.',
          'Ratings you give organizations and outcomes, and follow-up messages you add to your cases.',
          'Technical data needed to run the service safely, such as IP addresses used briefly for rate limiting.',
        ],
      },
      {
        h: 'How we use it',
        p: [
          'To deliver your gunaso to the organization you chose and record every step of how it is handled.',
          'To email you about your case, if you gave an email address and did not submit anonymously.',
          'To show public, aggregate statistics (such as how many cases an organization resolves) — never who filed them.',
          'To prevent abuse, spam and fraud.',
        ],
      },
      {
        h: 'Who can see what',
        p: [
          'The organization sees what you wrote and its full history. It sees your name only if you did not choose anonymous, and your email and phone are shown only to the staff who handle cases.',
          'Anyone with your reference number can see the public status page: what was reported, its status history and the organization’s replies. Internal staff notes and your contact details are never shown there.',
          'Only you — signed in, or holding the private follow-up link — can reply to the organization or rate the outcome.',
          'Gunaso platform staff can see identity on anonymous cases, strictly for abuse handling and legal obligations.',
        ],
      },
      {
        h: 'AI features',
        p: [
          'Organizations may use AI tools to categorise cases, draft replies and summarise trends. For this, the type, title and description of a case are sent to our AI provider (Anthropic). Your name, email and phone are never included — regardless of whether you submitted anonymously.',
        ],
      },
      {
        h: 'Cookies and storage on your device',
        p: [
          'A secure, http-only cookie keeps you signed in. Your browser also stores a few preferences (such as dark mode) and, if you filed without an account, the references and private links of cases filed from that device — so you can find them again. None of this is used for advertising or tracking.',
        ],
      },
      {
        h: 'How long we keep it',
        p: [
          'A case’s history is a permanent, append-only record — that is what makes it trustworthy. Attachments and contact details are kept for as long as the case exists. You can ask us to delete your account at any time.',
        ],
      },
      {
        h: 'Your choices',
        p: [
          'You can file without an account, file anonymously, and ask us for a copy or deletion of your personal data by contacting us. We will respond within a reasonable time and tell you if something must be kept (for example, to comply with the law).',
        ],
      },
      {
        h: 'Security',
        p: [
          'Traffic is encrypted, passwords are hashed, uploaded files are checked for type and content and are never executed, and every status change and platform-administration action is logged.',
        ],
      },
    ],
  },
  terms: {
    title: 'Terms of use',
    intro: 'By using Gunaso you agree to these terms. They are written to be read, not skimmed.',
    sections: [
      {
        h: 'What Gunaso is',
        p: [
          'Gunaso is a channel between citizens and organizations. We record and deliver your gunaso and keep a tamper-proof history of how it is handled. We do not decide the outcome, and we cannot guarantee that an organization will resolve it.',
        ],
      },
      {
        h: 'Using Gunaso fairly',
        p: [
          'Tell the truth. Do not file knowingly false or malicious reports, impersonate anyone, harass people, or post someone else’s private information.',
          'Do not upload illegal content, malware, or material you don’t have the right to share.',
          'Do not try to overload, scrape, probe or break the service, or to identify anonymous submitters.',
        ],
      },
      {
        h: 'Your content',
        p: [
          'You keep ownership of what you write. You allow us to store it, show it to the organization, and display it on the public status page as described in the privacy policy. Organizations may choose to showcase a case on their public profile; an anonymous case always stays anonymous.',
        ],
      },
      {
        h: 'Organizations',
        p: [
          'Organizations must be genuine, keep their profile accurate, respond to cases in good faith, and use citizens’ contact details only to handle the case they relate to. We verify organizations before listing them and may suspend any that misuse the platform.',
        ],
      },
      {
        h: 'Moderation',
        p: [
          'We may hide content or suspend accounts that break these terms or the law. Case histories are otherwise never edited.',
        ],
      },
      {
        h: 'No warranty',
        p: [
          'We work hard to keep Gunaso available and secure, but it is provided “as is”. To the extent the law allows, we are not liable for decisions organizations make or for indirect losses arising from use of the service.',
        ],
      },
      {
        h: 'Changes',
        p: [
          'We may update these terms. If a change is significant, we will say so on the site before it takes effect.',
        ],
      },
    ],
  },
  'child-safety': {
    title: 'Child safety standards',
    intro: 'Gunaso has zero tolerance for child sexual abuse and exploitation (CSAE), including child sexual abuse material (CSAM). This page sets out the standards that apply to everyone who uses Gunaso — on the web and in our Android and iOS apps — and how we act on reports.',
    sections: [
      {
        h: 'Our standard',
        p: [
          'Content or behaviour that sexualises, exploits, grooms or endangers children is strictly prohibited on Gunaso. This includes CSAM in any form — images, video, text or links — whether real, drawn or AI-generated.',
          'Gunaso is a civic complaint platform for adults. It is not directed at children, and it has no public social feed, user-to-user messaging or dating features.',
        ],
      },
      {
        h: 'How to report a concern in the app',
        p: [
          'Open Contact us (in the site footer) and choose “Child safety concern”. Reports go straight to Gunaso platform staff, not to any organization, and you do not need an account to send one.',
          'If you saw the content in a case, include its reference number (GUN-YYYY-NNNNN) so we can find it quickly.',
          'You can also email our child safety point of contact directly at techthimi@gmail.com.',
          'If a child is in immediate danger, contact local police first. In Nepal you can call Nepal Police on 100 or the child helpline on 1098.',
        ],
      },
      {
        h: 'What we do when we receive a report',
        p: [
          'Child safety reports are treated as the highest priority and reviewed by platform staff as quickly as possible.',
          'Content that breaches this standard is removed from public view, and the accounts involved are blocked; blocking also ends their active sessions.',
          'We preserve the relevant records and report apparent CSAM to the appropriate authorities — including Nepal Police and, where applicable, the National Center for Missing & Exploited Children (NCMEC) and other regional authorities — as required by law.',
          'We cooperate with law enforcement requests made through proper legal channels.',
        ],
      },
      {
        h: 'Compliance with the law',
        p: [
          'Gunaso complies with applicable child safety laws, including the laws of Nepal and the requirements of the app stores that distribute our apps.',
        ],
      },
      {
        h: 'Child safety point of contact',
        p: [
          'Our designated child safety contact can speak to our CSAM prevention practices and compliance: techthimi@gmail.com.',
        ],
      },
    ],
  },
}

const doc = computed(() => docs[props.page] || docs.privacy)
</script>

<template>
  <div class="bg-app-bg dark:bg-gray-900">
    <div class="page-container max-w-3xl py-14 sm:py-20">
      <p class="text-xs font-bold uppercase tracking-[0.2em] text-primary mb-3">Last updated {{ UPDATED }}</p>
      <h1 class="font-display text-4xl font-extrabold text-secondary dark:text-white tracking-tight mb-4">{{ doc.title }}</h1>
      <p class="text-lg text-gray-600 dark:text-gray-300 leading-relaxed mb-10">{{ doc.intro }}</p>

      <nav class="card p-5 mb-10" aria-label="On this page">
        <p class="text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">On this page</p>
        <ol class="grid sm:grid-cols-2 gap-x-6 gap-y-1 text-sm">
          <li v-for="(s, i) in doc.sections" :key="s.h"><a :href="`#s${i}`" class="text-secondary dark:text-gray-200 hover:text-primary">{{ i + 1 }}. {{ s.h }}</a></li>
        </ol>
      </nav>

      <section v-for="(s, i) in doc.sections" :id="`s${i}`" :key="s.h" class="mb-10 scroll-mt-24">
        <h2 class="font-display text-xl font-bold text-secondary dark:text-white mb-3">{{ i + 1 }}. {{ s.h }}</h2>
        <ul v-if="s.p.length > 1" class="space-y-2.5 list-disc pl-5 marker:text-primary">
          <li v-for="(para, j) in s.p" :key="j" class="text-gray-700 dark:text-gray-300 leading-relaxed">{{ para }}</li>
        </ul>
        <p v-else class="text-gray-700 dark:text-gray-300 leading-relaxed">{{ s.p[0] }}</p>
      </section>

      <div class="card p-6 mt-12">
        <p class="font-semibold text-gray-900 dark:text-white">Questions about this page?</p>
        <p class="text-sm text-gray-600 dark:text-gray-300 mt-1">
          <RouterLink to="/contact" class="text-primary font-semibold hover:underline">Contact us</RouterLink> — a person will reply.
          <template v-if="page !== 'terms'"> See also the <RouterLink to="/terms" class="text-primary hover:underline">terms of use</RouterLink>.</template>
          <template v-else> See also the <RouterLink to="/privacy" class="text-primary hover:underline">privacy policy</RouterLink>.</template>
        </p>
      </div>
    </div>
  </div>
</template>
