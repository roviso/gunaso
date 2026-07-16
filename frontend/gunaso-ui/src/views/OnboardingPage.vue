<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useOnboardingStore } from '@/stores/onboarding'

const router = useRouter()
const authStore = useAuthStore()
const onboardingStore = useOnboardingStore()

const step = ref(0)
const direction = ref('forward')
const totalSteps = 3

const firstName = computed(() => (authStore.user?.name || 'friend').split(' ')[0])
const isOrgAdmin = computed(() => authStore.isOrgAdmin)
const showsOrgWorkspace = computed(() => authStore.hasOrgAccess)

const lifecycle = [
  { label: 'Submitted', color: 'bg-amber-400' },
  { label: 'Acknowledged', color: 'bg-cyan-400' },
  { label: 'In Review', color: 'bg-blue-400' },
  { label: 'Resolved', color: 'bg-green-400' },
]

const howItWorks = [
  {
    title: 'Speak up',
    description: 'File a complaint, feedback, or suggestion to any registered organization — anonymously if you prefer.',
    icon: 'M7 8h10M7 12h6m-9 8l3.5-3.5H17a2 2 0 002-2V6a2 2 0 00-2-2H7a2 2 0 00-2 2v12.5z'
  },
  {
    title: 'Track everything',
    description: 'Every submission gets a unique GUN- reference number. Check its status any time — no account needed.',
    icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4'
  },
  {
    title: 'Hold them accountable',
    description: 'Every status change is recorded in a permanent audit trail that organizations can never edit or erase.',
    icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z'
  },
]

const citizenActions = [
  {
    key: 'submit', primary: true, to: '/submit',
    title: 'Submit my first complaint',
    description: 'Takes under 2 minutes. Attach evidence if you have it.',
    icon: 'M12 4v16m8-8H4'
  },
  {
    key: 'browse', to: '/organizations',
    title: 'Browse organizations',
    description: 'See who is registered and how they respond.',
    icon: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4'
  },
  {
    key: 'track', to: '/track',
    title: 'Track an existing complaint',
    description: 'Have a GUN- reference number? Look it up.',
    icon: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z'
  },
  {
    key: 'dashboard', to: '/dashboard',
    title: 'Go to my dashboard',
    description: 'I’ll explore on my own.',
    icon: 'M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z'
  },
]

const orgActions = [
  {
    key: 'org-register', primary: true, to: '/org/register',
    title: 'Set up my organization',
    description: 'Register your organization so citizens can reach you. Platform admins verify it before it goes public.',
    icon: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4'
  },
  {
    key: 'org-dashboard', to: '/org/dashboard',
    title: 'Go to my org dashboard',
    description: 'Manage incoming submissions, respond, and move them through the resolution workflow.',
    icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z'
  },
]

const staffActions = [
  {
    key: 'org-dashboard', primary: true, to: '/org/dashboard',
    title: 'Go to my org dashboard',
    description: 'View incoming submissions and take action where your role allows.',
    icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z'
  },
]

const actions = computed(() => {
  if (isOrgAdmin.value) return orgActions
  if (showsOrgWorkspace.value) return staffActions
  return citizenActions
})

function next() {
  if (step.value < totalSteps - 1) {
    direction.value = 'forward'
    step.value++
  }
}

function back() {
  if (step.value > 0) {
    direction.value = 'backward'
    step.value--
  }
}

function finish(to) {
  onboardingStore.markOnboarded(authStore.user?.id)
  router.push(to)
}

function skip() {
  finish(showsOrgWorkspace.value ? '/org/dashboard' : '/dashboard')
}

function onKeydown(e) {
  if (e.key === 'ArrowRight' || (e.key === 'Enter' && step.value < totalSteps - 1 && e.target.tagName !== 'BUTTON' && e.target.tagName !== 'A')) next()
  else if (e.key === 'ArrowLeft') back()
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  if (!isOrgAdmin.value) authStore.fetchStaffAccess()
})
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="h-full min-h-screen overflow-y-auto bg-gradient-to-br from-secondary via-[#16294a] to-secondary-900 text-white relative">
    <!-- Atmosphere -->
    <div class="pointer-events-none absolute top-0 right-0 w-[36rem] h-[36rem] bg-primary/15 rounded-full -translate-y-1/2 translate-x-1/3 blur-3xl" />
    <div class="pointer-events-none absolute bottom-0 left-0 w-96 h-96 bg-accent/20 rounded-full translate-y-1/2 -translate-x-1/4 blur-3xl" />
    <div class="pointer-events-none absolute inset-0 opacity-[0.04]"
      style="background-image: radial-gradient(currentColor 1px, transparent 1px); background-size: 28px 28px;" />

    <div class="relative min-h-screen flex flex-col max-w-3xl mx-auto px-4 sm:px-6 py-8">
      <!-- Top bar: progress + skip -->
      <header class="flex items-center justify-between gap-4">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 bg-primary rounded-lg flex items-center justify-center shadow-glow">
            <span class="text-white font-display font-extrabold text-sm leading-none">G</span>
          </div>
          <span class="font-display font-bold tracking-tight">Gunaso</span>
        </div>

        <div class="flex items-center gap-1.5" role="progressbar" :aria-valuenow="step + 1" :aria-valuemin="1" :aria-valuemax="totalSteps" aria-label="Onboarding progress">
          <span v-for="i in totalSteps" :key="i"
            :class="['h-1.5 rounded-full transition-all duration-500 ease-spring',
              i - 1 === step ? 'w-8 bg-primary' : i - 1 < step ? 'w-3 bg-primary/60' : 'w-3 bg-white/20']" />
        </div>

        <button @click="skip" class="text-sm text-blue-200/80 hover:text-white transition-colors font-medium">
          Skip for now
        </button>
      </header>

      <!-- Steps -->
      <main class="flex-1 flex flex-col justify-center py-10">
        <Transition :name="direction === 'forward' ? 'step-fwd' : 'step-back'" mode="out-in">

          <!-- STEP 1 · Welcome -->
          <section v-if="step === 0" key="welcome" class="text-center">
            <div class="stagger">
              <div class="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-primary shadow-glow mx-auto mb-8 animate-float-slow">
                <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z"/>
                </svg>
              </div>

              <p class="font-display text-5xl sm:text-6xl font-bold mb-3 tracking-tight">नमस्ते, {{ firstName }}</p>
              <h1 class="text-xl sm:text-2xl text-blue-100 font-medium mb-6">Welcome to Gunaso — your voice, on the record.</h1>

              <p class="text-blue-200/80 max-w-md mx-auto leading-relaxed">
                In the next 30 seconds we'll show you how Gunaso turns a complaint into
                a tracked, accountable process — then get you moving.
              </p>

              <div class="mt-10">
                <button @click="next" class="btn-primary px-10 py-4 text-base shadow-glow">
                  Let's go
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"/>
                  </svg>
                </button>
              </div>
            </div>
          </section>

          <!-- STEP 2 · How it works -->
          <section v-else-if="step === 1" key="how" class="text-center">
            <h1 class="font-display text-3xl sm:text-4xl font-bold tracking-tight mb-3 animate-fade-up">How Gunaso works</h1>
            <p class="text-blue-200/80 mb-10 animate-fade-up" style="animation-delay: 0.08s">
              Three ideas that make organizations actually listen.
            </p>

            <div class="grid sm:grid-cols-3 gap-4 text-left stagger">
              <div v-for="(item, i) in howItWorks" :key="i"
                class="rounded-2xl bg-white/[0.06] border border-white/10 backdrop-blur-sm p-5 hover:bg-white/[0.09] transition-colors">
                <div class="w-11 h-11 rounded-xl bg-primary/20 border border-primary/30 flex items-center justify-center mb-4">
                  <svg class="w-5 h-5 text-primary-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" :d="item.icon"/>
                  </svg>
                </div>
                <h3 class="font-display font-semibold mb-1.5">{{ item.title }}</h3>
                <p class="text-sm text-blue-200/75 leading-relaxed">{{ item.description }}</p>
              </div>
            </div>

            <!-- Live lifecycle strip -->
            <div class="mt-10 rounded-2xl bg-white/[0.04] border border-white/10 p-5 animate-fade-up" style="animation-delay: 0.5s">
              <p class="text-xs uppercase tracking-widest text-blue-300/70 font-semibold mb-4">Every submission moves through a public timeline</p>
              <div class="flex items-center justify-between max-w-lg mx-auto">
                <template v-for="(stage, i) in lifecycle" :key="stage.label">
                  <div class="flex flex-col items-center gap-2">
                    <span :class="['w-3 h-3 rounded-full', stage.color, i === 0 ? 'animate-pulse-dot' : '']" />
                    <span class="text-[11px] sm:text-xs text-blue-100/90 font-medium whitespace-nowrap">{{ stage.label }}</span>
                  </div>
                  <div v-if="i < lifecycle.length - 1"
                    class="flex-1 h-px bg-gradient-to-r from-white/30 to-white/10 mx-2 origin-left animate-draw-line"
                    :style="{ animationDelay: `${0.7 + i * 0.2}s` }" />
                </template>
              </div>
            </div>

            <div class="mt-10 flex items-center justify-center gap-3">
              <button @click="back" class="btn-ghost text-blue-200 hover:text-white hover:bg-white/10">Back</button>
              <button @click="next" class="btn-primary px-10 py-3.5">
                Got it
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"/>
                </svg>
              </button>
            </div>
          </section>

          <!-- STEP 3 · First action -->
          <section v-else key="action" class="text-center">
            <h1 class="font-display text-3xl sm:text-4xl font-bold tracking-tight mb-3 animate-fade-up">
              {{ isOrgAdmin ? 'Set up your workspace' : showsOrgWorkspace ? 'You\'re all set' : 'What would you like to do first?' }}
            </h1>
            <p class="text-blue-200/80 mb-10 animate-fade-up" style="animation-delay: 0.08s">
              {{ isOrgAdmin ? 'Get your organization ready to receive and resolve submissions.' : showsOrgWorkspace ? 'Head to your org dashboard to get started.' : 'Pick one — you can do everything else later.' }}
            </p>

            <div :class="['grid gap-4 text-left stagger', (isOrgAdmin || showsOrgWorkspace) ? 'sm:grid-cols-2 max-w-2xl mx-auto' : 'sm:grid-cols-2']">
              <button v-for="action in actions" :key="action.key" @click="finish(action.to)"
                :class="['group rounded-2xl p-5 border text-left transition-all duration-200 ease-spring hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.99]',
                  action.primary
                    ? 'bg-primary border-primary-400/50 shadow-glow hover:bg-primary-600'
                    : 'bg-white/[0.06] border-white/10 hover:bg-white/[0.1]']">
                <div class="flex items-start gap-4">
                  <div :class="['w-11 h-11 rounded-xl flex items-center justify-center shrink-0',
                    action.primary ? 'bg-white/20' : 'bg-primary/20 border border-primary/30']">
                    <svg :class="['w-5 h-5', action.primary ? 'text-white' : 'text-primary-300']"
                      fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" :d="action.icon"/>
                    </svg>
                  </div>
                  <div>
                    <p class="font-display font-semibold mb-1 flex items-center gap-1.5">
                      {{ action.title }}
                      <svg class="w-4 h-4 opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"/>
                      </svg>
                    </p>
                    <p :class="['text-sm leading-relaxed', action.primary ? 'text-white/85' : 'text-blue-200/75']">{{ action.description }}</p>
                  </div>
                </div>
              </button>
            </div>

            <div class="mt-10">
              <button @click="back" class="btn-ghost text-blue-200 hover:text-white hover:bg-white/10">Back</button>
            </div>
          </section>
        </Transition>
      </main>

      <footer class="text-center text-xs text-blue-300/50 pb-2">
        Anonymous submissions never reveal your identity to organizations.
      </footer>
    </div>
  </div>
</template>

<style scoped>
.step-fwd-enter-active, .step-back-enter-active { transition: all 0.35s cubic-bezier(0.22, 1, 0.36, 1); }
.step-fwd-leave-active, .step-back-leave-active { transition: all 0.22s ease-in; }
.step-fwd-enter-from { opacity: 0; transform: translateX(32px); }
.step-fwd-leave-to { opacity: 0; transform: translateX(-24px); }
.step-back-enter-from { opacity: 0; transform: translateX(-32px); }
.step-back-leave-to { opacity: 0; transform: translateX(24px); }
</style>
