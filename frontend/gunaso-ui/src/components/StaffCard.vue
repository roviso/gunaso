<script setup>
import { ref } from 'vue'
import { useOrganizationStore } from '@/stores/organization'
import { useUIStore } from '@/stores/ui'
import { apiErrorMessage } from '@/api/index'

const props = defineProps({
  member: { type: Object, required: true },
  canEdit: { type: Boolean, default: true },
})
const emit = defineEmits(['change-role', 'remove', 'resend-link'])

const orgStore = useOrganizationStore()
const uiStore = useUIStore()
const resending = ref(false)

// Roles are now admin-defined per organization, so we no longer hardcode a
// color per role name — every role gets the same generic pill style.
const ROLE_STYLE = 'bg-secondary/10 text-secondary dark:bg-white/10 dark:text-white'

const STATUS_STYLE = {
  invited:  'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  active:   'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  disabled: 'bg-red-100 text-red-600 dark:bg-red-900/20 dark:text-red-400',
}

const STATUS_LABEL = {
  invited: 'Invited',
  active: 'Active',
  disabled: 'Disabled',
}

function initial(m) {
  const name = m.user_name || m.name || m.user?.name || m.user_email || m.email || '?'
  return name[0].toUpperCase()
}

function displayName(m) {
  return m.user_name || m.name || m.user?.name || m.user_email || m.email || 'Unknown'
}

function displayEmail(m) {
  return m.user_email || m.email || m.user?.email || ''
}

function displayRole(m) {
  return m.role_name || 'Staff'
}

async function handleResendInvite() {
  const slug = orgStore.currentOrg?.slug
  if (!slug || resending.value) return
  resending.value = true
  try {
    const data = await orgStore.resendInvite(slug, props.member.id)
    if (data?.invite_link) emit('resend-link', data.invite_link)
    else uiStore.showSuccess('Invite resent.')
  } catch (err) {
    uiStore.showError(apiErrorMessage(err, 'Failed to resend invite.'))
  } finally {
    resending.value = false
  }
}
</script>

<template>
  <div class="card p-4 flex items-center gap-4">
    <!-- Avatar -->
    <div class="w-10 h-10 rounded-full bg-secondary text-white flex items-center justify-center text-sm font-bold shrink-0">
      {{ initial(member) }}
    </div>

    <!-- Info -->
    <div class="flex-1 min-w-0">
      <div class="flex items-center flex-wrap gap-2 mb-0.5">
        <p class="font-semibold text-gray-900 dark:text-white text-sm">{{ displayName(member) }}</p>
        <span :class="['px-2 py-0.5 rounded-full text-xs font-semibold', ROLE_STYLE]">
          {{ displayRole(member) }}
        </span>
        <span v-if="member.status" :class="['px-2 py-0.5 rounded-full text-xs font-semibold', STATUS_STYLE[member.status] || STATUS_STYLE.active]">
          {{ STATUS_LABEL[member.status] || member.status }}
        </span>
        <span v-else-if="member.is_active === false"
          class="px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-600 dark:bg-red-900/20 dark:text-red-400">
          Inactive
        </span>
      </div>
      <p class="text-xs text-gray-500 dark:text-gray-400">{{ displayEmail(member) }}</p>
      <p v-if="member.active_submissions_count !== undefined" class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
        {{ member.active_submissions_count }} active submissions
      </p>
    </div>

    <!-- Actions -->
    <div v-if="canEdit" class="flex items-center gap-1 shrink-0">
      <button v-if="member.status === 'invited'" @click="handleResendInvite" :disabled="resending"
        class="p-1.5 rounded-lg text-gray-400 hover:text-secondary dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
        title="Resend invite">
        <svg v-if="!resending" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
        </svg>
        <svg v-else class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
        </svg>
      </button>
      <button @click="$emit('change-role', member)"
        class="p-1.5 rounded-lg text-gray-400 hover:text-secondary dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        title="Edit role">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
        </svg>
      </button>
      <button @click="$emit('remove', member)"
        class="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/10 transition-colors"
        title="Remove">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
        </svg>
      </button>
    </div>
  </div>
</template>
