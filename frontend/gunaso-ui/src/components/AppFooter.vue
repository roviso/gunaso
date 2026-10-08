<script setup>
import BrandMark from '@/components/BrandMark.vue'

const links = {
  Citizens: [
    { label: 'File a gunaso', to: '/submit' },
    { label: 'Track a gunaso', to: '/track' },
    { label: 'Organizations', to: '/organizations' },
    { label: 'Map', to: '/map' },
    { label: 'My dashboard', to: '/dashboard' },
  ],
  Organizations: [
    { label: 'Why Gunaso', to: '/for-organizations' },
    { label: 'Register your organization', to: '/org/register' },
    { label: 'Organization dashboard', to: '/org/dashboard' },
    { label: 'Book a walkthrough', to: { name: 'Contact', query: { topic: 'organization' } } },
  ],
  Help: [
    { label: 'How it works', to: '/how-it-works' },
    { label: 'FAQ', to: '/how-it-works#faq' },
    { label: 'Contact us', to: '/contact' },
    { label: 'Privacy policy', to: '/privacy' },
    { label: 'Terms of use', to: '/terms' },
    { label: 'Child safety', to: '/child-safety' },
  ],
}
</script>

<template>
  <footer class="bg-secondary dark:bg-gray-950 text-white">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-14 pb-10">
      <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-[1.4fr,1fr,1fr,1fr] gap-8 mb-12">
        <div class="col-span-2 md:col-span-4 lg:col-span-1">
          <BrandMark :size="36" inverted />
          <p class="text-blue-200 text-sm leading-relaxed mt-4 max-w-xs">
            Nepal’s civic grievance platform. File a gunaso, follow it to an answer, and hold institutions accountable — on the record.
          </p>
          <p class="text-sm font-semibold text-primary-300 italic mt-4">“आफ्नो आवाज उठाउनुस्”</p>
          <p class="text-xs text-blue-300 mt-1">Raise your voice.</p>
        </div>

        <nav v-for="(items, group) in links" :key="group" :aria-label="group">
          <h2 class="font-bold text-xs text-white/90 mb-4 uppercase tracking-[0.15em]">{{ group }}</h2>
          <ul class="space-y-2.5">
            <li v-for="item in items" :key="item.label">
              <RouterLink :to="item.to" class="text-blue-200 hover:text-white text-sm transition-colors">
                {{ item.label }}
              </RouterLink>
            </li>
          </ul>
        </nav>
      </div>

      <div class="pt-8 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-blue-300">
        <p>© {{ new Date().getFullYear() }} Gunaso. Free for citizens, always.</p>
        <p class="flex items-center gap-2">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
          Anonymous submissions are never revealed to organizations.
        </p>
      </div>
    </div>
  </footer>
</template>
