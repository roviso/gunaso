<script setup>
const links = {
  Platform: [
    { label: 'Browse Organizations', to: '/organizations' },
    { label: 'Submit Complaint', to: '/submit' },
    { label: 'Track Complaint', to: '/track' },
    { label: 'Register Organization', to: '/org/register' },
  ],
  Account: [
    { label: 'Login', to: '/login' },
    { label: 'Register', to: '/register' },
    { label: 'My Submissions', to: '/dashboard' },
    { label: 'Org Dashboard', to: '/org/dashboard' },
  ],
  Support: [
    { label: 'How it Works', to: '/' },
    { label: 'FAQ', to: '/' },
    { label: 'Contact Us', to: '/' },
    { label: 'Privacy Policy', to: '/' },
  ]
}
</script>

<template>
  <footer class="bg-secondary dark:bg-gray-950 text-white">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mb-10">
        <!-- Brand -->
        <div>
          <div class="flex items-center gap-2 mb-4">
            <div class="w-9 h-9 bg-primary rounded-lg flex items-center justify-center">
              <span class="text-white font-extrabold">G</span>
            </div>
            <span class="text-xl font-extrabold tracking-tight">Gunaso</span>
          </div>
          <p class="text-blue-200 text-sm leading-relaxed mb-4">
            Nepal's civic grievance platform. Submit complaints, track resolutions, hold institutions accountable.
          </p>
          <p class="text-sm font-semibold text-primary-300 italic">"आफ्नो आवाज उठाउनुस्"</p>
          <p class="text-xs text-blue-300 mt-1">Raise your voice.</p>
        </div>

        <!-- Link Groups -->
        <div v-for="(items, group) in links" :key="group">
          <h4 class="font-bold text-sm text-white mb-4 uppercase tracking-wider">{{ group }}</h4>
          <ul class="space-y-2.5">
            <li v-for="item in items" :key="item.label">
              <RouterLink :to="item.to" class="text-blue-200 hover:text-white text-sm transition-colors hover:underline">
                {{ item.label }}
              </RouterLink>
            </li>
          </ul>
        </div>
      </div>

      <div class="pt-8 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-4">
        <p class="text-blue-300 text-sm">
          © {{ new Date().getFullYear() }} Gunaso. All rights reserved.
        </p>
        <div class="flex items-center gap-2">
          <span class="inline-flex items-center gap-1.5 text-xs text-blue-300 bg-white/10 px-3 py-1.5 rounded-full">
            <span class="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse"></span>
            System Operational
          </span>
        </div>
      </div>
    </div>
  </footer>
</template>
