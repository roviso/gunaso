import { defineStore } from 'pinia'
import { ref } from 'vue'

// Guest submitters have no account, so this device remembers the cases they
// filed here (reference + private follow-up key) to make following up a
// one-tap affair. Per-device convenience only, like the onboarding flag — it
// is never sent anywhere, and the page works without it (private windows,
// blocked storage).
const STORAGE_KEY = 'gunaso_saved_submissions'
const MAX_SAVED = 20

function read() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
    return Array.isArray(parsed) ? parsed.filter((e) => e && typeof e.ref === 'string') : []
  } catch {
    return []
  }
}

function write(entries) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries))
  } catch {
    /* storage unavailable — keep the in-memory copy only */
  }
}

export const useSavedSubmissionsStore = defineStore('savedSubmissions', () => {
  const entries = ref(read())

  function save({ ref: reference, key = '', organization = '', title = '' }) {
    if (!reference) return
    const existing = entries.value.find((e) => e.ref === reference)
    const entry = {
      ref: reference,
      // Never drop a key we already had just because a later visit lacked one.
      key: key || existing?.key || '',
      organization: organization || existing?.organization || '',
      title: title || existing?.title || '',
      savedAt: existing?.savedAt || new Date().toISOString(),
    }
    entries.value = [entry, ...entries.value.filter((e) => e.ref !== reference)].slice(0, MAX_SAVED)
    write(entries.value)
  }

  function keyFor(reference) {
    return entries.value.find((e) => e.ref === reference)?.key || ''
  }

  function remove(reference) {
    entries.value = entries.value.filter((e) => e.ref !== reference)
    write(entries.value)
  }

  return { entries, save, keyFor, remove }
})
