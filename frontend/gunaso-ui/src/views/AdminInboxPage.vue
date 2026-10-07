<script setup>
import { ref, watch, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'
import { useUIStore } from '@/stores/ui'
import { apiErrorMessage } from '@/api/index'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

// Public contact-form messages (apps/platform_admin ContactMessage).
const adminStore = useAdminStore()
const uiStore = useUIStore()

const filter = ref('open') // open | handled | all
const search = ref('')
const expanded = ref(null)
const busy = ref(null)

const TOPIC_CLS = {
  organization: 'bg-primary/10 text-primary',
  support: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  press: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300',
}

function load() {
  adminStore.fetchInbox({
    ...(filter.value === 'open' ? { is_handled: false } : filter.value === 'handled' ? { is_handled: true } : {}),
    ...(search.value.trim() ? { search: search.value.trim() } : {}),
  })
}

let timer = null
watch(search, () => {
  clearTimeout(timer)
  timer = setTimeout(load, 300)
})
watch(filter, load)

async function toggleHandled(message) {
  busy.value = message.id
  try {
    await adminStore.setMessageHandled(message.id, !message.is_handled)
    uiStore.showSuccess(message.is_handled ? 'Moved back to open.' : 'Marked as handled.')
    if (filter.value !== 'all') load()
  } catch (err) {
    uiStore.showError(apiErrorMessage(err, 'Could not update the message.'))
  } finally {
    busy.value = null
  }
}

function formatTimestamp(iso) {
  return new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })
}

onMounted(load)
</script>

<template>
  <div class="p-6 space-y-5">
    <div class="flex items-end justify-between gap-4 flex-wrap">
      <div>
        <h1 class="text-xl font-extrabold text-secondary dark:text-white">Inbox</h1>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Messages from the public contact form.</p>
      </div>
      <div class="flex items-center gap-2">
        <input v-model="search" type="search" placeholder="Search…" class="input-base !py-2 w-48" aria-label="Search messages" />
        <div class="flex p-1 rounded-xl bg-gray-100 dark:bg-gray-800">
          <button v-for="f in ['open', 'handled', 'all']" :key="f" @click="filter = f"
            :class="['px-3 py-1.5 rounded-lg text-xs font-semibold capitalize', filter === f ? 'bg-white dark:bg-gray-700 shadow-sm text-secondary dark:text-white' : 'text-gray-500']">
            {{ f }}
          </button>
        </div>
      </div>
    </div>

    <LoadingSpinner v-if="adminStore.inboxLoading" />
    <div v-else-if="adminStore.inboxError" class="card p-6 text-center text-sm text-red-500">{{ adminStore.inboxError }}</div>
    <div v-else-if="!adminStore.inbox.length" class="card p-12 text-center">
      <p class="font-semibold text-gray-700 dark:text-gray-200">{{ filter === 'open' ? 'Inbox zero 🎉' : 'No messages' }}</p>
    </div>

    <ul v-else class="card divide-y divide-gray-100 dark:divide-gray-700/50">
      <li v-for="m in adminStore.inbox" :key="m.id" class="p-4">
        <div class="flex items-start gap-4">
          <button class="flex-1 min-w-0 text-left" @click="expanded = expanded === m.id ? null : m.id">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-semibold text-sm text-gray-900 dark:text-white">{{ m.name }}</span>
              <span class="text-xs text-gray-500">&lt;{{ m.email }}&gt;</span>
              <span :class="['px-2 py-0.5 rounded-full text-[11px] font-semibold', TOPIC_CLS[m.topic] || 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300']">{{ m.topic_label }}</span>
              <span v-if="m.organization" class="text-xs text-gray-500">· {{ m.organization }}</span>
            </div>
            <p :class="['text-sm text-gray-600 dark:text-gray-300 mt-1 whitespace-pre-line', expanded === m.id ? '' : 'line-clamp-2']">{{ m.message }}</p>
            <p v-if="m.is_handled" class="text-xs text-green-600 mt-1">Handled by {{ m.handled_by_name }} · {{ formatTimestamp(m.handled_at) }}</p>
          </button>
          <div class="flex flex-col items-end gap-2 shrink-0">
            <span class="text-xs text-gray-400 whitespace-nowrap">{{ formatTimestamp(m.created_at) }}</span>
            <div class="flex gap-2">
              <a :href="`mailto:${encodeURIComponent(m.email)}?subject=${encodeURIComponent('Re: your message to Gunaso')}`"
                class="text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700">Reply</a>
              <button :disabled="busy === m.id" @click="toggleHandled(m)"
                :class="['text-xs font-semibold px-2.5 py-1.5 rounded-lg disabled:opacity-50', m.is_handled ? 'border border-gray-200 dark:border-gray-600' : 'bg-secondary text-white']">
                {{ m.is_handled ? 'Reopen' : 'Mark handled' }}
              </button>
            </div>
          </div>
        </div>
      </li>
    </ul>
  </div>
</template>
