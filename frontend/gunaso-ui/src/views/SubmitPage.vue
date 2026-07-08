<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useOrganizationStore } from '@/stores/organization'
import { useSubmissionStore } from '@/stores/submission'
import { useUIStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const router = useRouter()
const orgStore = useOrganizationStore()
const submissionStore = useSubmissionStore()
const uiStore = useUIStore()
const authStore = useAuthStore()

const currentStep = ref(1)
const orgSearch = ref('')
const selectedOrg = ref(null)
const submissionResult = ref(null)
const copied = ref(false)
const attachmentLabel = ref('')

const form = ref({
  type: 'complaint',
  category: '',
  title: '',
  description: '',
  priority: 'medium',
  attachment: null,
  submitter_name: '',
  submitter_email: '',
  submitter_phone: '',
  is_anonymous: false
})

const errors = ref({})

const ORG_CATEGORIES = {
  Telecom: ['Network Issue', 'Billing', 'Customer Service', 'Coverage', 'Data Speed', 'SIM / Account', 'Other'],
  Government: ['Service Delay', 'Corruption', 'Public Facility', 'Documentation', 'Staff Conduct', 'Other'],
  Bank: ['Account Issue', 'Transaction Error', 'Loan', 'ATM / Card', 'Customer Service', 'Fraud', 'Other'],
  Hospital: ['Treatment Quality', 'Staff Behavior', 'Facility', 'Billing', 'Appointment', 'Other'],
  Education: ['Admission', 'Fees', 'Staff', 'Facilities', 'Results', 'Other'],
  default: ['Service Quality', 'Billing', 'Staff Conduct', 'Delay', 'Facilities', 'General Feedback', 'Other']
}

const categories = computed(() => {
  if (!selectedOrg.value) return ORG_CATEGORIES.default
  return ORG_CATEGORIES[selectedOrg.value.category] || ORG_CATEGORIES.default
})

const filteredOrgs = computed(() => {
  const q = orgSearch.value.toLowerCase()
  if (!q) return orgStore.organizations
  return orgStore.organizations.filter(
    (o) => o.name.toLowerCase().includes(q) || o.category.toLowerCase().includes(q)
  )
})

const steps = [
  { num: 1, label: 'Select Organization' },
  { num: 2, label: 'Fill Details' },
  { num: 3, label: 'Confirmation' }
]

function selectOrg(org) {
  selectedOrg.value = org
  form.value.category = ''
}

function clearOrg() {
  selectedOrg.value = null
  orgSearch.value = ''
  form.value.category = ''
}

function handleFileChange(e) {
  const file = e.target.files[0]
  if (file) {
    form.value.attachment = file
    attachmentLabel.value = file.name
  }
}

function validate() {
  errors.value = {}
  if (!form.value.category) errors.value.category = 'Please select a category.'
  if (!form.value.title.trim()) errors.value.title = 'Title is required.'
  else if (form.value.title.trim().length < 5) errors.value.title = 'Title must be at least 5 characters.'
  if (!form.value.description.trim()) errors.value.description = 'Description is required.'
  else if (form.value.description.trim().length < 20) errors.value.description = 'Please provide more detail (min. 20 characters).'
  if (!form.value.is_anonymous) {
    if (!form.value.submitter_name.trim()) errors.value.submitter_name = 'Name is required unless submitting anonymously.'
    if (!form.value.submitter_email.trim()) errors.value.submitter_email = 'Email is required unless submitting anonymously.'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.value.submitter_email)) errors.value.submitter_email = 'Enter a valid email address.'
  }
  return Object.keys(errors.value).length === 0
}

async function handleSubmit() {
  if (!validate()) {
    const firstError = document.querySelector('[data-error]')
    firstError?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    return
  }
  try {
    const payload = {
      organization: selectedOrg.value.id,
      ...form.value
    }
    const result = await submissionStore.createSubmission(payload)
    submissionResult.value = result
    currentStep.value = 3
    uiStore.showSuccess('Complaint submitted successfully!')
  } catch {
    uiStore.showError(submissionStore.error || 'Submission failed. Please try again.')
  }
}

async function copyReference() {
  await navigator.clipboard.writeText(submissionResult.value.reference_number)
  copied.value = true
  setTimeout(() => (copied.value = false), 2000)
}

function resetForm() {
  currentStep.value = 1
  selectedOrg.value = null
  orgSearch.value = ''
  submissionResult.value = null
  copied.value = false
  form.value = {
    type: 'complaint', category: '', title: '', description: '',
    priority: 'medium', attachment: null,
    submitter_name: '', submitter_email: '', submitter_phone: '', is_anonymous: false
  }
  errors.value = {}
}

// When navigated to /submit/:orgSlug the org is locked (QR code flow)
const lockedSlug = computed(() => route.params.orgSlug || null)
const isLocked = computed(() => !!lockedSlug.value)

onMounted(async () => {
  await orgStore.fetchOrganizations()

  // Route param takes priority (QR code flow)
  const slugParam = lockedSlug.value || route.query.org
  if (slugParam) {
    const found = orgStore.organizations.find((o) => o.slug === slugParam)
    if (found) {
      selectedOrg.value = found
      currentStep.value = 2
    } else {
      // Try fetching directly if not in list
      await orgStore.fetchOrgBySlug(slugParam)
      if (orgStore.currentOrg) {
        selectedOrg.value = orgStore.currentOrg
        currentStep.value = 2
      }
    }
  }

  // Pre-fill contact info if logged in
  if (authStore.isAuthenticated && authStore.user) {
    form.value.submitter_name = authStore.user.name || ''
    form.value.submitter_email = authStore.user.email || ''
  }
})
</script>

<template>
  <div class="bg-app-bg dark:bg-gray-900 min-h-[calc(100vh-4rem)]">
    <!-- Page header -->
    <div class="bg-gradient-to-br from-secondary to-[#0f1f38] text-white py-10">
      <div class="page-container">
        <h1 class="text-3xl font-extrabold mb-1">Submit Complaint / Feedback</h1>
        <p class="text-blue-200 text-sm">Your submission is recorded and forwarded to the organization immediately.</p>
      </div>
    </div>

    <!-- Stepper -->
    <div class="bg-white dark:bg-gray-800 border-b border-gray-100 dark:border-gray-700 shadow-sm">
      <div class="page-container py-4">
        <div class="flex items-center max-w-lg">
          <template v-for="(step, idx) in steps" :key="step.num">
            <div class="flex items-center gap-2">
              <div :class="['w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all duration-200',
                currentStep > step.num ? 'bg-green-500 text-white' :
                currentStep === step.num ? 'bg-primary text-white shadow-md shadow-primary/30' :
                'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400']">
                <svg v-if="currentStep > step.num" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
                </svg>
                <span v-else>{{ step.num }}</span>
              </div>
              <span :class="['text-xs font-semibold hidden sm:block transition-colors',
                currentStep === step.num ? 'text-primary' : currentStep > step.num ? 'text-green-600' : 'text-gray-400 dark:text-gray-500']">
                {{ step.label }}
              </span>
            </div>
            <div v-if="idx < steps.length - 1" :class="['flex-1 h-0.5 mx-3 transition-colors',
              currentStep > step.num ? 'bg-green-400' : 'bg-gray-200 dark:bg-gray-700']" />
          </template>
        </div>
      </div>
    </div>

    <div class="page-container py-8">
      <div class="max-w-2xl mx-auto">

        <!-- ===== STEP 1: SELECT ORG ===== -->
        <div v-if="currentStep === 1" class="card p-6">
          <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-1">Select Organization</h2>
          <p class="text-sm text-gray-500 dark:text-gray-400 mb-5">Which organization would you like to submit feedback to?</p>

          <!-- Already selected -->
          <div v-if="selectedOrg" class="mb-5 flex items-center gap-3 bg-primary/5 dark:bg-primary/10 border border-primary/20 rounded-xl p-4">
            <div class="w-10 h-10 bg-primary/20 rounded-xl flex items-center justify-center font-bold text-primary">
              {{ selectedOrg.name[0] }}
            </div>
            <div class="flex-1">
              <p class="font-semibold text-gray-900 dark:text-white text-sm">{{ selectedOrg.name }}</p>
              <p class="text-xs text-gray-500 dark:text-gray-400">{{ selectedOrg.category }}</p>
            </div>
            <button @click="clearOrg" class="text-xs text-gray-400 hover:text-red-500 dark:hover:text-red-400 transition-colors font-medium">
              Change
            </button>
          </div>

          <LoadingSpinner v-if="orgStore.loading" size="sm" label="Loading organizations..." />

          <template v-else>
            <input v-model="orgSearch" type="text" placeholder="Search organizations..."
              class="input-base mb-3" />

            <div class="space-y-2 max-h-72 overflow-y-auto pr-1 scrollbar-thin">
              <button v-for="org in filteredOrgs" :key="org.id"
                @click="selectOrg(org)"
                :class="['w-full flex items-center gap-3 p-3 rounded-xl border text-left transition-all duration-150',
                  selectedOrg?.id === org.id
                    ? 'border-primary bg-primary/5 dark:bg-primary/10'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700/50']">
                <div class="w-9 h-9 bg-secondary/10 dark:bg-gray-700 rounded-lg flex items-center justify-center text-secondary dark:text-white font-bold text-sm shrink-0">
                  {{ org.name[0] }}
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-1.5">
                    <span class="text-sm font-semibold text-gray-900 dark:text-white truncate">{{ org.name }}</span>
                    <svg v-if="org.verified" class="w-3.5 h-3.5 text-blue-500 shrink-0" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                    </svg>
                  </div>
                  <span class="text-xs text-gray-400 dark:text-gray-500">{{ org.category }}</span>
                </div>
                <div v-if="selectedOrg?.id === org.id" class="w-5 h-5 bg-primary rounded-full flex items-center justify-center shrink-0">
                  <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/>
                  </svg>
                </div>
              </button>

              <div v-if="!filteredOrgs.length" class="text-center py-8 text-gray-400 dark:text-gray-500 text-sm">
                No organizations match "{{ orgSearch }}"
              </div>
            </div>
          </template>

          <button @click="currentStep = 2" :disabled="!selectedOrg"
            class="btn-primary w-full mt-5 py-3.5 disabled:opacity-40">
            Continue with {{ selectedOrg?.name || 'Selected Organization' }}
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
            </svg>
          </button>
        </div>

        <!-- ===== STEP 2: FILL FORM ===== -->
        <div v-else-if="currentStep === 2" class="space-y-5">
          <!-- Selected org banner (locked when coming from QR code) -->
          <div :class="['flex items-center gap-3 border rounded-2xl p-4 shadow-sm',
            isLocked
              ? 'bg-primary/5 dark:bg-primary/10 border-primary/20'
              : 'bg-white dark:bg-gray-800 border-gray-100 dark:border-gray-700']">
            <div class="w-10 h-10 bg-secondary rounded-xl flex items-center justify-center text-white font-bold shrink-0">
              {{ selectedOrg?.name[0] }}
            </div>
            <div class="flex-1">
              <p v-if="isLocked" class="text-xs font-semibold text-primary uppercase tracking-wider mb-0.5">
                Submitting feedback for
              </p>
              <p class="font-semibold text-gray-900 dark:text-white text-sm">{{ selectedOrg?.name }}</p>
              <p class="text-xs text-gray-500 dark:text-gray-400">{{ selectedOrg?.category }}</p>
            </div>
            <button v-if="!isLocked" @click="currentStep = 1"
              class="text-xs text-gray-400 hover:text-primary transition-colors font-medium shrink-0">
              Change
            </button>
            <span v-else class="shrink-0">
              <svg class="w-5 h-5 text-primary" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd"/>
              </svg>
            </span>
          </div>

          <div class="card p-6">
            <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-5">Complaint Details</h2>

            <form @submit.prevent="handleSubmit" class="space-y-5">
              <!-- Type -->
              <div>
                <label class="label">Type</label>
                <div class="grid grid-cols-3 gap-2">
                  <label v-for="t in [{ value: 'complaint', label: '⚠️ Complaint' }, { value: 'feedback', label: '💬 Feedback' }, { value: 'suggestion', label: '💡 Suggestion' }]" :key="t.value"
                    :class="['flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl border cursor-pointer transition-all text-xs font-semibold',
                      form.type === t.value ? 'border-primary bg-primary/5 text-primary dark:bg-primary/10' : 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-500']">
                    <input type="radio" :value="t.value" v-model="form.type" class="sr-only" />
                    {{ t.label }}
                  </label>
                </div>
              </div>

              <!-- Category -->
              <div data-error>
                <label class="label">Category *</label>
                <select v-model="form.category" :class="['input-base', errors.category ? 'border-red-400' : '']">
                  <option value="">Select a category</option>
                  <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
                </select>
                <p v-if="errors.category" class="field-error">{{ errors.category }}</p>
              </div>

              <!-- Title -->
              <div>
                <label class="label">Title *</label>
                <input v-model="form.title" type="text" placeholder="Brief summary of your complaint"
                  :class="['input-base', errors.title ? 'border-red-400' : '']"
                  maxlength="150" />
                <div class="flex justify-between mt-1">
                  <p v-if="errors.title" class="field-error">{{ errors.title }}</p>
                  <p class="text-xs text-gray-400 dark:text-gray-500 ml-auto">{{ form.title.length }}/150</p>
                </div>
              </div>

              <!-- Description -->
              <div>
                <label class="label">Description *</label>
                <textarea v-model="form.description" rows="5"
                  placeholder="Describe your complaint in detail. Include dates, reference numbers, and what outcome you expect..."
                  :class="['input-base resize-none', errors.description ? 'border-red-400' : '']"
                  maxlength="2000" />
                <div class="flex justify-between mt-1">
                  <p v-if="errors.description" class="field-error">{{ errors.description }}</p>
                  <p class="text-xs text-gray-400 dark:text-gray-500 ml-auto">{{ form.description.length }}/2000</p>
                </div>
              </div>

              <!-- Priority -->
              <div>
                <label class="label">Priority</label>
                <div class="grid grid-cols-4 gap-2">
                  <label v-for="p in [{ v: 'low', l: 'Low', c: 'text-slate-600' }, { v: 'medium', l: 'Medium', c: 'text-yellow-600' }, { v: 'high', l: 'High', c: 'text-orange-600' }, { v: 'urgent', l: 'Urgent', c: 'text-red-600' }]" :key="p.v"
                    :class="['flex items-center justify-center py-2 rounded-xl border cursor-pointer transition-all text-xs font-bold',
                      form.priority === p.v ? 'border-current bg-current/5 ' + p.c : 'border-gray-200 dark:border-gray-600 text-gray-500 dark:text-gray-400 hover:border-gray-300 dark:hover:border-gray-500']">
                    <input type="radio" :value="p.v" v-model="form.priority" class="sr-only" />
                    {{ p.l }}
                  </label>
                </div>
              </div>

              <!-- Attachment -->
              <div>
                <label class="label">Attachment (optional)</label>
                <label class="flex items-center gap-3 p-3.5 border-2 border-dashed border-gray-200 dark:border-gray-600 rounded-xl cursor-pointer hover:border-primary/40 hover:bg-primary/2 dark:hover:border-primary/40 transition-colors">
                  <svg class="w-5 h-5 text-gray-400 dark:text-gray-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"/>
                  </svg>
                  <span class="text-sm text-gray-500 dark:text-gray-400">
                    {{ attachmentLabel || 'Click to upload screenshot or document' }}
                  </span>
                  <input type="file" class="sr-only" accept="image/*,.pdf,.doc,.docx" @change="handleFileChange" />
                </label>
                <p class="text-xs text-gray-400 dark:text-gray-500 mt-1.5">Supported: JPG, PNG, PDF, DOC (max 5MB)</p>
              </div>

              <!-- Anonymous toggle -->
              <div class="flex items-start gap-3 p-4 bg-gray-50 dark:bg-gray-700/40 rounded-xl">
                <div class="relative mt-0.5">
                  <input type="checkbox" id="anon" v-model="form.is_anonymous" class="sr-only peer" />
                  <div @click="form.is_anonymous = !form.is_anonymous"
                    :class="['w-10 h-5 rounded-full cursor-pointer transition-colors duration-200', form.is_anonymous ? 'bg-primary' : 'bg-gray-300 dark:bg-gray-600']">
                    <div :class="['w-4 h-4 bg-white rounded-full shadow absolute top-0.5 transition-transform duration-200', form.is_anonymous ? 'translate-x-5' : 'translate-x-0.5']" />
                  </div>
                </div>
                <div>
                  <label for="anon" class="text-sm font-semibold text-gray-900 dark:text-white cursor-pointer">Submit Anonymously</label>
                  <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Your identity will not be shared with the organization.</p>
                </div>
              </div>

              <!-- Submitter info (if not anonymous) -->
              <Transition name="slide">
                <div v-if="!form.is_anonymous" class="space-y-4 p-4 bg-blue-50 dark:bg-blue-900/15 border border-blue-100 dark:border-blue-800 rounded-xl">
                  <p class="text-xs font-semibold text-blue-700 dark:text-blue-400 uppercase tracking-wider">Your Contact Information</p>
                  <div>
                    <label class="label">Full Name *</label>
                    <input v-model="form.submitter_name" type="text" placeholder="Ram Prasad Sharma"
                      :class="['input-base', errors.submitter_name ? 'border-red-400' : '']" />
                    <p v-if="errors.submitter_name" class="field-error">{{ errors.submitter_name }}</p>
                  </div>
                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label class="label">Email *</label>
                      <input v-model="form.submitter_email" type="email" placeholder="you@example.com"
                        :class="['input-base', errors.submitter_email ? 'border-red-400' : '']" />
                      <p v-if="errors.submitter_email" class="field-error">{{ errors.submitter_email }}</p>
                    </div>
                    <div>
                      <label class="label">Phone (optional)</label>
                      <input v-model="form.submitter_phone" type="tel" placeholder="+977-98XXXXXXXX" class="input-base" />
                    </div>
                  </div>
                </div>
              </Transition>

              <div class="flex gap-3 pt-2">
                <button type="button" @click="currentStep = 1" class="btn-secondary px-5">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
                  </svg>
                  Back
                </button>
                <button type="submit" :disabled="submissionStore.loading" class="btn-primary flex-1 py-3.5 text-base">
                  <svg v-if="submissionStore.loading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  {{ submissionStore.loading ? 'Submitting...' : 'Submit Complaint' }}
                </button>
              </div>
            </form>
          </div>
        </div>

        <!-- ===== STEP 3: SUCCESS ===== -->
        <div v-else-if="currentStep === 3 && submissionResult" class="card p-8 text-center">
          <!-- Success icon -->
          <div class="w-20 h-20 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg class="w-10 h-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
            </svg>
          </div>

          <h2 class="text-2xl font-extrabold text-gray-900 dark:text-white mb-2">Complaint Submitted!</h2>
          <p class="text-gray-500 dark:text-gray-400 text-sm mb-8">
            Your complaint has been submitted to <span class="font-semibold text-gray-900 dark:text-white">{{ submissionResult.organization_name || selectedOrg?.name }}</span> and is now pending review.
          </p>

          <!-- Reference number -->
          <div class="bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-2xl p-6 mb-6">
            <p class="text-xs text-gray-500 dark:text-gray-400 mb-2 font-medium uppercase tracking-wider">Your Reference Number</p>
            <p class="text-3xl font-extrabold text-secondary dark:text-white font-mono tracking-widest mb-4">
              {{ submissionResult.reference_number }}
            </p>
            <button @click="copyReference"
              :class="['w-full py-2.5 rounded-xl text-sm font-semibold border transition-all duration-200 flex items-center justify-center gap-2',
                copied ? 'bg-green-500 border-green-500 text-white' : 'border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:border-primary hover:text-primary dark:hover:text-primary']">
              <svg v-if="!copied" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
              </svg>
              <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
              </svg>
              {{ copied ? 'Copied!' : 'Copy Reference Number' }}
            </button>
          </div>

          <p class="text-xs text-gray-500 dark:text-gray-400 mb-6">
            Save this reference number to track your complaint status at any time.
          </p>

          <!-- Actions -->
          <div class="flex flex-col sm:flex-row gap-3">
            <RouterLink :to="{ name: 'Track', query: { ref: submissionResult.reference_number } }"
              class="btn-primary flex-1 justify-center py-3">
              Track This Complaint
            </RouterLink>
            <button @click="resetForm" class="btn-secondary flex-1 py-3">Submit Another</button>
          </div>

          <div v-if="!authStore.isAuthenticated" class="mt-5 p-4 bg-secondary/5 dark:bg-secondary/15 border border-secondary/10 rounded-xl">
            <p class="text-sm text-gray-700 dark:text-gray-300">
              <span class="font-semibold">Create a free account</span> to track all your submissions in one place.
            </p>
            <RouterLink to="/register" class="text-primary text-sm font-semibold hover:underline mt-1 inline-block">
              Register now →
            </RouterLink>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<style scoped>
.slide-enter-active, .slide-leave-active { transition: all 0.25s ease; }
.slide-enter-from, .slide-leave-to { opacity: 0; transform: translateY(-8px); max-height: 0; overflow: hidden; }
.slide-enter-to, .slide-leave-from { max-height: 500px; }
</style>
