<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useOrganizationStore } from '@/stores/organization'
import { useUIStore } from '@/stores/ui'
import { apiErrorMessage } from '@/api/index'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import LocationPicker from '@/components/LocationPicker.vue'

const authStore = useAuthStore()
const orgStore = useOrganizationStore()
const uiStore = useUIStore()

const slug = computed(() => orgStore.currentOrg?.slug)
const canManage = computed(() => authStore.hasPrivilege('manage_branches'))

function emptyForm() {
  return { name: '', address: '', latitude: null, longitude: null, is_active: true }
}

// ===== Create modal =====
const showCreateModal = ref(false)
const createForm = ref(emptyForm())
const createError = ref('')
const creating = ref(false)

function openCreate() {
  createForm.value = emptyForm()
  createError.value = ''
  showCreateModal.value = true
}

function closeCreate() {
  showCreateModal.value = false
  createError.value = ''
}

async function submitCreate() {
  if (!createForm.value.name.trim() || creating.value) return
  creating.value = true
  createError.value = ''
  try {
    await orgStore.createBranch(slug.value, createForm.value)
    uiStore.showSuccess('Branch created.')
    closeCreate()
  } catch (err) {
    createError.value = apiErrorMessage(err, 'Failed to create branch.')
  } finally {
    creating.value = false
  }
}

// ===== Edit modal =====
const showEditModal = ref(false)
const branchToEdit = ref(null)
const editForm = ref(emptyForm())
const editError = ref('')
const saving = ref(false)

function openEdit(branch) {
  branchToEdit.value = branch
  editForm.value = {
    name: branch.name,
    address: branch.address || '',
    latitude: branch.latitude != null ? Number(branch.latitude) : null,
    longitude: branch.longitude != null ? Number(branch.longitude) : null,
    is_active: branch.is_active,
  }
  editError.value = ''
  showEditModal.value = true
}

function closeEdit() {
  showEditModal.value = false
  editError.value = ''
  branchToEdit.value = null
}

async function submitEdit() {
  if (!branchToEdit.value || !editForm.value.name.trim() || saving.value) return
  saving.value = true
  editError.value = ''
  try {
    await orgStore.updateBranch(slug.value, branchToEdit.value.id, editForm.value)
    uiStore.showSuccess('Branch updated.')
    closeEdit()
  } catch (err) {
    editError.value = apiErrorMessage(err, 'Failed to update branch.')
  } finally {
    saving.value = false
  }
}

// ===== Delete flow =====
const showConfirm = ref(false)
const branchToDelete = ref(null)
const deleteError = ref('')
const deleting = ref(false)

function openDelete(branch) {
  branchToDelete.value = branch
  deleteError.value = ''
  showConfirm.value = true
}

function closeDelete() {
  showConfirm.value = false
  branchToDelete.value = null
  deleteError.value = ''
}

async function confirmDelete() {
  if (!branchToDelete.value || deleting.value) return
  deleting.value = true
  deleteError.value = ''
  try {
    await orgStore.deleteBranch(slug.value, branchToDelete.value.id)
    uiStore.showSuccess('Branch deleted.')
    closeDelete()
  } catch (err) {
    deleteError.value = apiErrorMessage(err, 'Failed to delete branch.')
  } finally {
    deleting.value = false
  }
}

onMounted(async () => {
  if (slug.value) await orgStore.fetchBranches(slug.value)
})
</script>

<template>
  <div class="p-6 space-y-5">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-extrabold text-secondary dark:text-white">Branches</h1>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
          Add your organization's physical locations — each gets its own QR code and map pin,
          so you can trace which branch a gunaso came from.
        </p>
      </div>
      <button v-if="canManage" @click="openCreate" class="btn-primary text-sm px-4 py-2.5 shrink-0">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
        Add Branch
      </button>
    </div>

    <LoadingSpinner v-if="orgStore.branchesLoading" />

    <div v-else-if="orgStore.branchesError" class="card p-6 text-center">
      <p class="text-sm text-red-500 dark:text-red-400">{{ orgStore.branchesError }}</p>
    </div>

    <div v-else-if="!orgStore.branches.length" class="card p-12 text-center">
      <div class="w-14 h-14 rounded-2xl bg-gray-100 dark:bg-gray-700 flex items-center justify-center mx-auto mb-4">
        <svg class="w-7 h-7 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
        </svg>
      </div>
      <p class="font-semibold text-gray-700 dark:text-gray-200">No branches yet</p>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1 mb-4">
        Add a branch to place it on the map and get it its own QR code.
      </p>
      <button v-if="canManage" @click="openCreate" class="btn-primary text-sm px-5">Add Your First Branch</button>
    </div>

    <div v-else class="space-y-3">
      <div v-for="branch in orgStore.branches" :key="branch.id" class="card p-4">
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <div class="flex items-center flex-wrap gap-2 mb-1">
              <p class="font-semibold text-gray-900 dark:text-white text-sm">{{ branch.name }}</p>
              <span v-if="!branch.is_active"
                class="px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400">
                Inactive
              </span>
              <span v-if="branch.latitude == null || branch.longitude == null"
                class="px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                No location set
              </span>
              <span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                {{ branch.submission_count }} gunaso
              </span>
            </div>
            <p v-if="branch.address" class="text-xs text-gray-500 dark:text-gray-400 mt-1">{{ branch.address }}</p>
            <p class="text-xs text-gray-400 dark:text-gray-500 mt-1 font-mono">Code: {{ branch.code }}</p>
          </div>
          <div v-if="canManage" class="flex items-center gap-1 shrink-0">
            <button @click="openEdit(branch)"
              class="p-1.5 rounded-lg text-gray-400 hover:text-secondary dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              title="Edit branch">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
              </svg>
            </button>
            <button @click="openDelete(branch)"
              class="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/10 transition-colors"
              title="Delete branch">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== CREATE BRANCH MODAL ===== -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="closeCreate" />
          <div class="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-lg border border-gray-100 dark:border-gray-700 p-6 max-h-[85vh] overflow-y-auto">
            <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-5">Add Branch</h2>
            <div class="space-y-5">
              <div>
                <label class="label">Branch Name *</label>
                <input v-model="createForm.name" type="text" placeholder="e.g. Thamel Branch" class="input-base" />
              </div>
              <div>
                <label class="label">Address (optional)</label>
                <input v-model="createForm.address" type="text" class="input-base" />
              </div>
              <div>
                <label class="label">Location (optional)</label>
                <p class="text-xs text-gray-400 dark:text-gray-500 mb-2">Click the map to place this branch.</p>
                <LocationPicker :model-value="{ latitude: createForm.latitude, longitude: createForm.longitude }"
                  @update:model-value="(loc) => { createForm.latitude = loc.latitude; createForm.longitude = loc.longitude }"
                  height="h-48" />
              </div>
              <p v-if="createError" class="field-error">{{ createError }}</p>
            </div>
            <div class="flex gap-3 mt-6">
              <button @click="closeCreate" class="btn-secondary flex-1 py-2.5 text-sm">Cancel</button>
              <button @click="submitCreate" :disabled="!createForm.name.trim() || creating"
                class="btn-primary flex-1 py-2.5 text-sm disabled:opacity-50">
                <svg v-if="creating" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                {{ creating ? 'Creating…' : 'Add Branch' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- ===== EDIT BRANCH MODAL ===== -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showEditModal && branchToEdit" class="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="closeEdit" />
          <div class="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-lg border border-gray-100 dark:border-gray-700 p-6 max-h-[85vh] overflow-y-auto">
            <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-5">Edit Branch</h2>
            <div class="space-y-5">
              <div>
                <label class="label">Branch Name *</label>
                <input v-model="editForm.name" type="text" class="input-base" />
              </div>
              <div>
                <label class="label">Address (optional)</label>
                <input v-model="editForm.address" type="text" class="input-base" />
              </div>
              <div>
                <label class="label">Location (optional)</label>
                <LocationPicker :model-value="{ latitude: editForm.latitude, longitude: editForm.longitude }"
                  @update:model-value="(loc) => { editForm.latitude = loc.latitude; editForm.longitude = loc.longitude }"
                  height="h-48" />
              </div>
              <div class="flex items-center justify-between gap-4 pt-2 border-t border-gray-100 dark:border-gray-700">
                <p class="text-sm font-semibold text-gray-900 dark:text-white">Active</p>
                <button type="button" role="switch" :aria-checked="editForm.is_active"
                  @click="editForm.is_active = !editForm.is_active"
                  :class="['relative inline-flex h-6 w-11 rounded-full transition-colors duration-200 shrink-0',
                    editForm.is_active ? 'bg-primary' : 'bg-gray-300 dark:bg-gray-600']">
                  <span :class="['inline-block h-5 w-5 mt-0.5 rounded-full bg-white shadow transform transition-transform duration-200',
                    editForm.is_active ? 'translate-x-[22px]' : 'translate-x-0.5']" />
                </button>
              </div>
              <p v-if="editError" class="field-error">{{ editError }}</p>
            </div>
            <div class="flex gap-3 mt-6">
              <button @click="closeEdit" class="btn-secondary flex-1 py-2.5 text-sm">Cancel</button>
              <button @click="submitEdit" :disabled="!editForm.name.trim() || saving"
                class="btn-primary flex-1 py-2.5 text-sm disabled:opacity-50">
                {{ saving ? 'Saving…' : 'Save Changes' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- ===== CONFIRM DELETE ===== -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showConfirm && branchToDelete" class="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="closeDelete" />
          <div class="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-sm border border-gray-100 dark:border-gray-700 p-6">
            <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-2">Delete Branch?</h2>
            <p class="text-sm text-gray-600 dark:text-gray-300 mb-5">
              Delete <span class="font-semibold">{{ branchToDelete.name }}</span>? Its QR code will stop working.
              Past gunaso already linked to it keep their record. This action cannot be undone.
            </p>
            <p v-if="deleteError" class="field-error mb-4">{{ deleteError }}</p>
            <div class="flex gap-3">
              <button @click="closeDelete" class="btn-secondary flex-1 py-2.5 text-sm">Cancel</button>
              <button @click="confirmDelete" :disabled="deleting"
                class="flex-1 py-2.5 text-sm font-semibold rounded-xl bg-red-500 hover:bg-red-600 text-white transition-colors disabled:opacity-50">
                {{ deleting ? 'Deleting…' : 'Delete' }}
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
