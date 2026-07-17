<script setup>
import { ref, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import { apiErrorMessage } from '@/api/index'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const adminStore = useAdminStore()
const authStore = useAuthStore()
const uiStore = useUIStore()

const search = ref('')
const userTypeFilter = ref('')
const busyId = ref(null)

const confirmAction = ref(null) // { type: 'block' | 'demote', user }
const confirming = ref(false)

async function load() {
  const params = {}
  if (search.value) params.search = search.value
  if (userTypeFilter.value) params.user_type = userTypeFilter.value
  await adminStore.fetchUsers(params)
}

function openConfirm(type, user) {
  confirmAction.value = { type, user }
}

async function runAction(type, userId) {
  busyId.value = userId
  try {
    if (type === 'block') {
      await adminStore.blockUser(userId)
      uiStore.showSuccess('User blocked.')
    } else if (type === 'unblock') {
      await adminStore.unblockUser(userId)
      uiStore.showSuccess('User unblocked.')
    } else if (type === 'promote') {
      await adminStore.promoteUser(userId)
      uiStore.showSuccess('User promoted to superadmin.')
    } else if (type === 'demote') {
      await adminStore.demoteUser(userId)
      uiStore.showSuccess('Superadmin access revoked.')
    }
  } catch (err) {
    uiStore.showError(apiErrorMessage(err, 'Could not complete this action.'))
  } finally {
    busyId.value = null
  }
}

async function confirmAndRun() {
  if (!confirmAction.value) return
  confirming.value = true
  await runAction(confirmAction.value.type, confirmAction.value.user.id)
  confirming.value = false
  confirmAction.value = null
}

async function promote(user) {
  await runAction('promote', user.id)
}

async function unblock(user) {
  await runAction('unblock', user.id)
}

onMounted(load)
</script>

<template>
  <div class="p-6 space-y-5">
    <div>
      <h1 class="text-xl font-extrabold text-secondary dark:text-white">Users</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
        Every account on the platform — block, unblock, or grant superadmin access.
      </p>
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap gap-3">
      <input v-model="search" @keydown.enter="load" type="text" placeholder="Search by name, email, username…"
        class="input-base max-w-xs" />
      <select v-model="userTypeFilter" @change="load" class="input-base w-auto">
        <option value="">All user types</option>
        <option value="citizen">Citizen</option>
        <option value="org_admin">Org Admin</option>
        <option value="stakeholder">Stakeholder</option>
      </select>
      <button @click="load" class="btn-secondary text-sm px-4">Search</button>
    </div>

    <LoadingSpinner v-if="adminStore.usersLoading" />

    <div v-else-if="adminStore.usersError" class="card p-6 text-center">
      <p class="text-sm text-red-500 dark:text-red-400">{{ adminStore.usersError }}</p>
    </div>

    <div v-else-if="!adminStore.users.length" class="card p-12 text-center">
      <p class="font-semibold text-gray-700 dark:text-gray-200">No users match this filter</p>
    </div>

    <div v-else class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 dark:bg-gray-900 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            <tr>
              <th class="px-4 py-3">User</th>
              <th class="px-4 py-3">Type</th>
              <th class="px-4 py-3">Organization</th>
              <th class="px-4 py-3">Status</th>
              <th class="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 dark:divide-gray-700/50">
            <tr v-for="user in adminStore.users" :key="user.id">
              <td class="px-4 py-3">
                <p class="font-semibold text-gray-900 dark:text-white">{{ user.name }}</p>
                <p class="text-xs text-gray-400 dark:text-gray-500">{{ user.email }}</p>
              </td>
              <td class="px-4 py-3 text-gray-600 dark:text-gray-300 capitalize">{{ user.user_type.replace('_', ' ') }}</td>
              <td class="px-4 py-3 text-gray-600 dark:text-gray-300">{{ user.organization_name || '—' }}</td>
              <td class="px-4 py-3">
                <div class="flex flex-wrap gap-1">
                  <span :class="['inline-flex w-fit items-center px-2.5 py-1 rounded-full text-xs font-semibold',
                    user.is_active
                      ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                      : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400']">
                    {{ user.is_active ? 'Active' : 'Blocked' }}
                  </span>
                  <span v-if="user.is_superuser" class="inline-flex w-fit items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
                    Superadmin
                  </span>
                </div>
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center justify-end gap-2 flex-wrap">
                  <button v-if="user.is_active" @click="openConfirm('block', user)"
                    :disabled="busyId === user.id || user.id === authStore.user?.id"
                    :title="user.id === authStore.user?.id ? 'You cannot block your own account' : ''"
                    class="text-xs font-semibold px-3 py-1.5 rounded-lg border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-40">
                    Block
                  </button>
                  <button v-else @click="unblock(user)" :disabled="busyId === user.id"
                    class="text-xs font-semibold px-3 py-1.5 rounded-lg border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20 transition-colors disabled:opacity-50">
                    Unblock
                  </button>

                  <button v-if="!user.is_superuser" @click="promote(user)" :disabled="busyId === user.id"
                    class="text-xs font-semibold px-3 py-1.5 rounded-lg border border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-colors disabled:opacity-50">
                    Promote
                  </button>
                  <button v-else @click="openConfirm('demote', user)"
                    :disabled="busyId === user.id || user.id === authStore.user?.id"
                    :title="user.id === authStore.user?.id ? 'You cannot demote your own account' : ''"
                    class="text-xs font-semibold px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-40">
                    Demote
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Confirm block/demote -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="confirmAction" class="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="confirmAction = null" />
          <div class="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-sm border border-gray-100 dark:border-gray-700 p-6">
            <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-2">
              {{ confirmAction.type === 'block' ? 'Block this user?' : 'Revoke superadmin access?' }}
            </h2>
            <p class="text-sm text-gray-600 dark:text-gray-300 mb-5">
              <span class="font-semibold">{{ confirmAction.user.name }}</span>
              <template v-if="confirmAction.type === 'block'">
                will be signed out everywhere and unable to log back in until unblocked.
              </template>
              <template v-else>
                will lose all superadmin powers, including access to this dashboard.
              </template>
            </p>
            <div class="flex gap-3">
              <button @click="confirmAction = null" class="btn-secondary flex-1 py-2.5 text-sm">Cancel</button>
              <button @click="confirmAndRun" :disabled="confirming"
                class="flex-1 py-2.5 text-sm font-semibold rounded-xl bg-red-500 hover:bg-red-600 text-white transition-colors disabled:opacity-50">
                {{ confirming ? 'Working…' : 'Confirm' }}
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
