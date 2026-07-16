<script setup>
import { ref, computed, onMounted } from 'vue'
import { useOrganizationStore } from '@/stores/organization'
import { useUIStore } from '@/stores/ui'
import { apiErrorMessage } from '@/api/index'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const orgStore = useOrganizationStore()
const uiStore = useUIStore()

const slug = computed(() => orgStore.currentOrg?.slug)

// Group labels for the privilege catalog's `group` field. Falls back to the
// raw key (capitalized) for any group not listed here, so a new backend
// group never breaks the UI.
const GROUP_LABELS = {
  submissions: 'Submissions',
  reporting: 'Reporting',
  staff: 'Staff',
  organization: 'Organization',
}

function groupLabel(group) {
  return GROUP_LABELS[group] || (group ? group[0].toUpperCase() + group.slice(1) : 'Other')
}

const privilegeGroups = computed(() => {
  const groups = new Map()
  for (const priv of orgStore.privilegeCatalog) {
    const key = priv.group || 'other'
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(priv)
  }
  return Array.from(groups.entries()).map(([group, privileges]) => ({
    group,
    label: groupLabel(group),
    privileges,
  }))
})

function privilegeLabel(key) {
  const priv = orgStore.privilegeCatalog.find((p) => p.key === key)
  return priv ? priv.label : key
}

// ===== Create modal =====
const showCreateModal = ref(false)
const createForm = ref({ name: '', privileges: [] })
const createError = ref('')
const creating = ref(false)

function openCreate() {
  createForm.value = { name: '', privileges: [] }
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
    await orgStore.createRole(slug.value, {
      name: createForm.value.name.trim(),
      privileges: createForm.value.privileges,
    })
    uiStore.showSuccess('Role created.')
    closeCreate()
  } catch (err) {
    createError.value = apiErrorMessage(err, 'Failed to create role.')
  } finally {
    creating.value = false
  }
}

// ===== Edit modal =====
const showEditModal = ref(false)
const roleToEdit = ref(null)
const editForm = ref({ name: '', privileges: [] })
const editError = ref('')
const saving = ref(false)

function openEdit(role) {
  roleToEdit.value = role
  editForm.value = { name: role.name, privileges: [...(role.privileges || [])] }
  editError.value = ''
  showEditModal.value = true
}

function closeEdit() {
  showEditModal.value = false
  editError.value = ''
  roleToEdit.value = null
}

async function submitEdit() {
  if (!roleToEdit.value || !editForm.value.name.trim() || saving.value) return
  saving.value = true
  editError.value = ''
  try {
    await orgStore.updateRole(slug.value, roleToEdit.value.id, {
      name: editForm.value.name.trim(),
      privileges: editForm.value.privileges,
    })
    uiStore.showSuccess('Role updated.')
    closeEdit()
  } catch (err) {
    editError.value = apiErrorMessage(err, 'Failed to update role.')
  } finally {
    saving.value = false
  }
}

// ===== Delete flow =====
const showConfirm = ref(false)
const roleToDelete = ref(null)
const deleteError = ref('')
const deleting = ref(false)

function openDelete(role) {
  roleToDelete.value = role
  deleteError.value = ''
  showConfirm.value = true
}

function closeDelete() {
  showConfirm.value = false
  roleToDelete.value = null
  deleteError.value = ''
}

async function confirmDelete() {
  if (!roleToDelete.value || deleting.value) return
  deleting.value = true
  deleteError.value = ''
  try {
    await orgStore.deleteRole(slug.value, roleToDelete.value.id)
    uiStore.showSuccess('Role deleted.')
    closeDelete()
  } catch (err) {
    // Surfaces the backend's 409 "role in use" response as a readable
    // message instead of letting a raw error/stack trace reach the user.
    deleteError.value = apiErrorMessage(err, 'Failed to delete role.')
  } finally {
    deleting.value = false
  }
}

onMounted(async () => {
  await orgStore.fetchPrivilegeCatalog()
  if (slug.value) await orgStore.fetchRoles(slug.value)
})
</script>

<template>
  <div class="p-6 space-y-5">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-extrabold text-secondary dark:text-white">Roles</h1>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Build custom roles with tailored privileges for your team.</p>
      </div>
      <button @click="openCreate" class="btn-primary text-sm px-4 py-2.5">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
        Create Role
      </button>
    </div>

    <LoadingSpinner v-if="orgStore.rolesLoading" />

    <div v-else-if="orgStore.rolesError" class="card p-6 text-center">
      <p class="text-sm text-red-500 dark:text-red-400">{{ orgStore.rolesError }}</p>
      <p class="text-xs text-gray-400 dark:text-gray-500 mt-2">The roles endpoint may not be available on your backend yet.</p>
    </div>

    <div v-else-if="!orgStore.roles.length" class="card p-12 text-center">
      <div class="w-14 h-14 rounded-2xl bg-gray-100 dark:bg-gray-700 flex items-center justify-center mx-auto mb-4">
        <svg class="w-7 h-7 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
        </svg>
      </div>
      <p class="font-semibold text-gray-700 dark:text-gray-200">No custom roles yet</p>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1 mb-4">Create roles to give staff members precise, scoped privileges.</p>
      <button @click="openCreate" class="btn-primary text-sm px-5">Create Your First Role</button>
    </div>

    <div v-else class="space-y-3">
      <div v-for="role in orgStore.roles" :key="role.id" class="card p-4">
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <div class="flex items-center flex-wrap gap-2 mb-1">
              <p class="font-semibold text-gray-900 dark:text-white text-sm">{{ role.name }}</p>
              <span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                {{ role.staff_count }} {{ role.staff_count === 1 ? 'member' : 'members' }}
              </span>
            </div>
            <div v-if="role.privileges?.length" class="flex flex-wrap gap-1.5 mt-2">
              <span v-for="key in role.privileges" :key="key"
                class="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                {{ privilegeLabel(key) }}
              </span>
            </div>
            <p v-else class="text-xs text-gray-400 dark:text-gray-500 mt-2">No privileges assigned.</p>
          </div>
          <div class="flex items-center gap-1 shrink-0">
            <button @click="openEdit(role)"
              class="p-1.5 rounded-lg text-gray-400 hover:text-secondary dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              title="Edit role">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
              </svg>
            </button>
            <button @click="openDelete(role)"
              class="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/10 transition-colors"
              title="Delete role">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== CREATE ROLE MODAL ===== -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="closeCreate" />
          <div class="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-lg border border-gray-100 dark:border-gray-700 p-6 max-h-[85vh] overflow-y-auto">
            <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-5">Create Role</h2>
            <div class="space-y-5">
              <div>
                <label class="label">Role Name *</label>
                <input v-model="createForm.name" type="text" placeholder="e.g. Regional Supervisor" class="input-base" />
              </div>
              <div>
                <label class="label">Privileges</label>
                <LoadingSpinner v-if="orgStore.privilegeCatalogLoading" size="sm" />
                <p v-else-if="orgStore.privilegeCatalogError" class="text-sm text-red-500 dark:text-red-400">
                  {{ orgStore.privilegeCatalogError }}
                </p>
                <div v-else class="space-y-4">
                  <div v-for="group in privilegeGroups" :key="group.group">
                    <p class="text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-2">
                      {{ group.label }}
                    </p>
                    <div class="space-y-2">
                      <label v-for="priv in group.privileges" :key="priv.key"
                        class="flex items-start gap-2.5 cursor-pointer select-none">
                        <input type="checkbox" :value="priv.key" v-model="createForm.privileges"
                          class="mt-0.5 rounded border-gray-300 text-primary focus:ring-primary" />
                        <span class="text-sm text-gray-700 dark:text-gray-200">{{ priv.label }}</span>
                      </label>
                    </div>
                  </div>
                </div>
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
                {{ creating ? 'Creating…' : 'Create Role' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- ===== EDIT ROLE MODAL ===== -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showEditModal && roleToEdit" class="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="closeEdit" />
          <div class="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-lg border border-gray-100 dark:border-gray-700 p-6 max-h-[85vh] overflow-y-auto">
            <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-5">Edit Role</h2>
            <div class="space-y-5">
              <div>
                <label class="label">Role Name *</label>
                <input v-model="editForm.name" type="text" class="input-base" />
              </div>
              <div>
                <label class="label">Privileges</label>
                <LoadingSpinner v-if="orgStore.privilegeCatalogLoading" size="sm" />
                <p v-else-if="orgStore.privilegeCatalogError" class="text-sm text-red-500 dark:text-red-400">
                  {{ orgStore.privilegeCatalogError }}
                </p>
                <div v-else class="space-y-4">
                  <div v-for="group in privilegeGroups" :key="group.group">
                    <p class="text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-2">
                      {{ group.label }}
                    </p>
                    <div class="space-y-2">
                      <label v-for="priv in group.privileges" :key="priv.key"
                        class="flex items-start gap-2.5 cursor-pointer select-none">
                        <input type="checkbox" :value="priv.key" v-model="editForm.privileges"
                          class="mt-0.5 rounded border-gray-300 text-primary focus:ring-primary" />
                        <span class="text-sm text-gray-700 dark:text-gray-200">{{ priv.label }}</span>
                      </label>
                    </div>
                  </div>
                </div>
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
        <div v-if="showConfirm && roleToDelete" class="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="closeDelete" />
          <div class="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-sm border border-gray-100 dark:border-gray-700 p-6">
            <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-2">Delete Role?</h2>
            <p class="text-sm text-gray-600 dark:text-gray-300 mb-5">
              Delete <span class="font-semibold">{{ roleToDelete.name }}</span>? This action cannot be undone.
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
