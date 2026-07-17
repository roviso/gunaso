<script setup>
import { ref, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'
import { useUIStore } from '@/stores/ui'
import { apiErrorMessage } from '@/api/index'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const adminStore = useAdminStore()
const uiStore = useUIStore()

const search = ref('')
const verifiedFilter = ref('') // '', 'true', 'false'
const busySlug = ref(null)

async function load() {
  const params = {}
  if (search.value) params.search = search.value
  if (verifiedFilter.value) params.is_verified = verifiedFilter.value
  await adminStore.fetchOrganizations(params)
}

async function toggleVerified(org) {
  busySlug.value = org.slug
  try {
    await adminStore.updateOrganization(org.slug, { is_verified: !org.is_verified })
    uiStore.showSuccess(org.is_verified ? 'Organization unverified.' : 'Organization verified.')
  } catch (err) {
    uiStore.showError(apiErrorMessage(err, 'Could not update this organization.'))
  } finally {
    busySlug.value = null
  }
}

async function toggleActive(org) {
  busySlug.value = org.slug
  try {
    await adminStore.updateOrganization(org.slug, { is_active: !org.is_active })
    uiStore.showSuccess(org.is_active ? 'Organization deactivated.' : 'Organization reactivated.')
  } catch (err) {
    uiStore.showError(apiErrorMessage(err, 'Could not update this organization.'))
  } finally {
    busySlug.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="p-6 space-y-5">
    <div>
      <h1 class="text-xl font-extrabold text-secondary dark:text-white">Organizations</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
        Verify newly registered organizations and manage every org on the platform.
      </p>
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap gap-3">
      <input v-model="search" @keydown.enter="load" type="text" placeholder="Search by name, category, email…"
        class="input-base max-w-xs" />
      <select v-model="verifiedFilter" @change="load" class="input-base w-auto">
        <option value="">All organizations</option>
        <option value="true">Verified only</option>
        <option value="false">Pending verification</option>
      </select>
      <button @click="load" class="btn-secondary text-sm px-4">Search</button>
    </div>

    <LoadingSpinner v-if="adminStore.organizationsLoading" />

    <div v-else-if="adminStore.organizationsError" class="card p-6 text-center">
      <p class="text-sm text-red-500 dark:text-red-400">{{ adminStore.organizationsError }}</p>
    </div>

    <div v-else-if="!adminStore.organizations.length" class="card p-12 text-center">
      <p class="font-semibold text-gray-700 dark:text-gray-200">No organizations match this filter</p>
    </div>

    <div v-else class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 dark:bg-gray-900 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            <tr>
              <th class="px-4 py-3">Organization</th>
              <th class="px-4 py-3">Admin</th>
              <th class="px-4 py-3">Category</th>
              <th class="px-4 py-3">Submissions</th>
              <th class="px-4 py-3">Status</th>
              <th class="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 dark:divide-gray-700/50">
            <tr v-for="org in adminStore.organizations" :key="org.id">
              <td class="px-4 py-3">
                <p class="font-semibold text-gray-900 dark:text-white">{{ org.name }}</p>
                <p class="text-xs text-gray-400 dark:text-gray-500">{{ org.slug }}</p>
              </td>
              <td class="px-4 py-3 text-gray-600 dark:text-gray-300">
                <p>{{ org.admin_name }}</p>
                <p class="text-xs text-gray-400 dark:text-gray-500">{{ org.admin_email }}</p>
              </td>
              <td class="px-4 py-3 text-gray-600 dark:text-gray-300 capitalize">{{ org.category }}</td>
              <td class="px-4 py-3 text-gray-600 dark:text-gray-300">{{ org.submission_count }}</td>
              <td class="px-4 py-3">
                <div class="flex flex-col gap-1">
                  <span :class="['inline-flex w-fit items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold',
                    org.is_verified
                      ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                      : 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300']">
                    {{ org.is_verified ? 'Verified' : 'Pending' }}
                  </span>
                  <span v-if="!org.is_active" class="inline-flex w-fit items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
                    Deactivated
                  </span>
                </div>
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center justify-end gap-2">
                  <button @click="toggleVerified(org)" :disabled="busySlug === org.slug"
                    class="text-xs font-semibold px-3 py-1.5 rounded-lg border transition-colors disabled:opacity-50"
                    :class="org.is_verified
                      ? 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                      : 'border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20'">
                    {{ org.is_verified ? 'Unverify' : 'Verify' }}
                  </button>
                  <button @click="toggleActive(org)" :disabled="busySlug === org.slug"
                    class="text-xs font-semibold px-3 py-1.5 rounded-lg border transition-colors disabled:opacity-50"
                    :class="org.is_active
                      ? 'border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20'
                      : 'border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20'">
                    {{ org.is_active ? 'Deactivate' : 'Reactivate' }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
