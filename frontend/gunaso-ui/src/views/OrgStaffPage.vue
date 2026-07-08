<script setup>
import { ref, computed, onMounted } from 'vue'
import { useOrganizationStore } from '@/stores/organization'
import { useUIStore } from '@/stores/ui'
import { apiErrorMessage } from '@/api/index'
import StaffCard from '@/components/StaffCard.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const orgStore = useOrganizationStore()
const uiStore = useUIStore()

const showAddModal = ref(false)
const showEditModal = ref(false)
const showConfirm = ref(false)
const memberToEdit = ref(null)
const memberToRemove = ref(null)

const addForm = ref({ user_email: '', role: 'agent' })
const addError = ref('')
const adding = ref(false)

const editRole = ref('agent')
const saving = ref(false)
const removing = ref(false)

const ROLES = ['manager', 'supervisor', 'agent', 'viewer']

const slug = computed(() => orgStore.currentOrg?.slug)

async function submitAddStaff() {
  if (!addForm.value.user_email || adding.value) return
  adding.value = true
  addError.value = ''
  try {
    await orgStore.addStaff(slug.value, addForm.value)
    uiStore.showSuccess('Staff member added.')
    showAddModal.value = false
    addForm.value = { user_email: '', role: 'agent' }
  } catch (err) {
    addError.value = typeof err === 'string' ? err : apiErrorMessage(err, 'Failed to add staff member.')
  } finally {
    adding.value = false
  }
}

function openEditRole(member) {
  memberToEdit.value = member
  editRole.value = member.role || 'agent'
  showEditModal.value = true
}

async function submitEditRole() {
  if (!memberToEdit.value || saving.value) return
  saving.value = true
  try {
    await orgStore.updateStaffRole(slug.value, memberToEdit.value.id, editRole.value)
    uiStore.showSuccess('Role updated.')
    showEditModal.value = false
    memberToEdit.value = null
  } catch (err) {
    uiStore.showError(typeof err === 'string' ? err : apiErrorMessage(err, 'Failed to update role.'))
  } finally {
    saving.value = false
  }
}

function openRemove(member) {
  memberToRemove.value = member
  showConfirm.value = true
}

async function confirmRemove() {
  if (!memberToRemove.value || removing.value) return
  removing.value = true
  try {
    await orgStore.removeStaff(slug.value, memberToRemove.value.id)
    uiStore.showSuccess('Staff member removed.')
  } catch (err) {
    uiStore.showError(typeof err === 'string' ? err : apiErrorMessage(err, 'Failed to remove staff member.'))
  } finally {
    removing.value = false
    showConfirm.value = false
    memberToRemove.value = null
  }
}

onMounted(async () => {
  if (slug.value) await orgStore.fetchStaff(slug.value)
})
</script>

<template>
  <div class="p-6 space-y-5">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-extrabold text-secondary dark:text-white">Staff</h1>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Manage your team members and their roles.</p>
      </div>
      <button @click="showAddModal = true" class="btn-primary text-sm px-4 py-2.5">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
        Add Staff
      </button>
    </div>

    <LoadingSpinner v-if="orgStore.staffLoading" />

    <div v-else-if="orgStore.staffError" class="card p-6 text-center">
      <p class="text-sm text-red-500 dark:text-red-400">{{ orgStore.staffError }}</p>
      <p class="text-xs text-gray-400 dark:text-gray-500 mt-2">The staff endpoint may not be available on your backend yet.</p>
    </div>

    <div v-else-if="!orgStore.staff.length" class="card p-12 text-center">
      <div class="w-14 h-14 rounded-2xl bg-gray-100 dark:bg-gray-700 flex items-center justify-center mx-auto mb-4">
        <svg class="w-7 h-7 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
        </svg>
      </div>
      <p class="font-semibold text-gray-700 dark:text-gray-200">No staff members yet</p>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1 mb-4">Add staff members to help manage submissions.</p>
      <button @click="showAddModal = true" class="btn-primary text-sm px-5">Add Your First Staff Member</button>
    </div>

    <div v-else class="space-y-3">
      <StaffCard
        v-for="member in orgStore.staff"
        :key="member.id"
        :member="member"
        @change-role="openEditRole"
        @remove="openRemove" />
    </div>

    <!-- ===== ADD STAFF MODAL ===== -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showAddModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showAddModal = false; addError = ''" />
          <div class="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-md border border-gray-100 dark:border-gray-700 p-6">
            <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-5">Add Staff Member</h2>
            <div class="space-y-4">
              <div>
                <label class="label">Email Address *</label>
                <input v-model="addForm.user_email" type="email" placeholder="staff@example.com"
                  class="input-base" @keydown.enter="submitAddStaff" />
              </div>
              <div>
                <label class="label">Role</label>
                <select v-model="addForm.role" class="input-base">
                  <option v-for="r in ROLES" :key="r" :value="r" class="capitalize">{{ r }}</option>
                </select>
              </div>
              <p v-if="addError" class="field-error">{{ addError }}</p>
            </div>
            <div class="flex gap-3 mt-6">
              <button @click="showAddModal = false; addError = ''" class="btn-secondary flex-1 py-2.5 text-sm">Cancel</button>
              <button @click="submitAddStaff" :disabled="!addForm.user_email || adding"
                class="btn-primary flex-1 py-2.5 text-sm disabled:opacity-50">
                <svg v-if="adding" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                {{ adding ? 'Adding…' : 'Add Staff' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- ===== EDIT ROLE MODAL ===== -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showEditModal && memberToEdit" class="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showEditModal = false" />
          <div class="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-sm border border-gray-100 dark:border-gray-700 p-6">
            <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-1">Change Role</h2>
            <p class="text-sm text-gray-500 dark:text-gray-400 mb-5">
              {{ memberToEdit.name || memberToEdit.email }}
            </p>
            <select v-model="editRole" class="input-base">
              <option v-for="r in ROLES" :key="r" :value="r" class="capitalize">{{ r }}</option>
            </select>
            <div class="flex gap-3 mt-6">
              <button @click="showEditModal = false" class="btn-secondary flex-1 py-2.5 text-sm">Cancel</button>
              <button @click="submitEditRole" :disabled="saving"
                class="btn-primary flex-1 py-2.5 text-sm disabled:opacity-50">
                {{ saving ? 'Saving…' : 'Save Role' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- ===== CONFIRM REMOVE ===== -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showConfirm && memberToRemove" class="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showConfirm = false" />
          <div class="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-sm border border-gray-100 dark:border-gray-700 p-6">
            <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-2">Remove Staff Member?</h2>
            <p class="text-sm text-gray-600 dark:text-gray-300 mb-5">
              Remove
              <span class="font-semibold">{{ memberToRemove.name || memberToRemove.email }}</span>
              from your organization? This action cannot be undone.
            </p>
            <div class="flex gap-3">
              <button @click="showConfirm = false; memberToRemove = null" class="btn-secondary flex-1 py-2.5 text-sm">Cancel</button>
              <button @click="confirmRemove" :disabled="removing"
                class="flex-1 py-2.5 text-sm font-semibold rounded-xl bg-red-500 hover:bg-red-600 text-white transition-colors disabled:opacity-50">
                {{ removing ? 'Removing…' : 'Remove' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: all 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>
