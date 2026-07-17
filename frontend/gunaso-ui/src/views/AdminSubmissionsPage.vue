<script setup>
import { ref, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'
import StatusBadge from '@/components/StatusBadge.vue'
import PriorityBadge from '@/components/PriorityBadge.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const adminStore = useAdminStore()

const search = ref('')
const statusFilter = ref('')

async function load() {
  const params = {}
  if (search.value) params.search = search.value
  if (statusFilter.value) params.status = statusFilter.value
  await adminStore.fetchSubmissions(params)
}

onMounted(load)
</script>

<template>
  <div class="p-6 space-y-5">
    <div>
      <h1 class="text-xl font-extrabold text-secondary dark:text-white">Submissions</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
        Every submission across every organization, including anonymous submitter identity.
      </p>
    </div>

    <div class="flex flex-wrap gap-3">
      <input v-model="search" @keydown.enter="load" type="text" placeholder="Search by title or reference…"
        class="input-base max-w-xs" />
      <select v-model="statusFilter" @change="load" class="input-base w-auto">
        <option value="">All statuses</option>
        <option value="submitted">Submitted</option>
        <option value="acknowledged">Acknowledged</option>
        <option value="in_review">In Review</option>
        <option value="resolved">Resolved</option>
        <option value="rejected">Rejected</option>
        <option value="escalated">Escalated</option>
        <option value="closed">Closed</option>
      </select>
      <button @click="load" class="btn-secondary text-sm px-4">Search</button>
    </div>

    <LoadingSpinner v-if="adminStore.submissionsLoading" />

    <div v-else-if="adminStore.submissionsError" class="card p-6 text-center">
      <p class="text-sm text-red-500 dark:text-red-400">{{ adminStore.submissionsError }}</p>
    </div>

    <div v-else-if="!adminStore.submissions.length" class="card p-12 text-center">
      <p class="font-semibold text-gray-700 dark:text-gray-200">No submissions match this filter</p>
    </div>

    <div v-else class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 dark:bg-gray-900 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            <tr>
              <th class="px-4 py-3">Reference</th>
              <th class="px-4 py-3">Title</th>
              <th class="px-4 py-3">Organization</th>
              <th class="px-4 py-3">Submitter</th>
              <th class="px-4 py-3">Priority</th>
              <th class="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 dark:divide-gray-700/50">
            <tr v-for="sub in adminStore.submissions" :key="sub.id">
              <td class="px-4 py-3 font-mono text-xs text-gray-500 dark:text-gray-400">{{ sub.reference_number }}</td>
              <td class="px-4 py-3 font-medium text-gray-900 dark:text-white max-w-xs truncate">{{ sub.title }}</td>
              <td class="px-4 py-3 text-gray-600 dark:text-gray-300">{{ sub.organization_name }}</td>
              <td class="px-4 py-3 text-gray-600 dark:text-gray-300">
                {{ sub.submitter_name || 'Anonymous' }}
                <span v-if="sub.is_anonymous" class="text-xs text-amber-600 dark:text-amber-400 ml-1">(anon)</span>
              </td>
              <td class="px-4 py-3"><PriorityBadge :priority="sub.priority" /></td>
              <td class="px-4 py-3"><StatusBadge :status="sub.status" /></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
