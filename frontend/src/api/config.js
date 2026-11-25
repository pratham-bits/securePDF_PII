import { api } from './client.js'

// Limits the server publishes at /api/config. Shown to people, never trusted:
// the server enforces every one of them.
export const DEFAULT_CONFIG = {
  retention_hours: null, // unknown until the server answers
  max_upload_mb: 20,
  max_pages: 30,
  invite_required: false,
}

let cached = null

export function fetchConfig() {
  if (!cached) {
    cached = api
      .get('/config')
      .then((data) => ({ ...DEFAULT_CONFIG, ...data }))
      .catch(() => {
        cached = null // try again next time
        return DEFAULT_CONFIG
      })
  }
  return cached
}

export function resetConfigCache() {
  cached = null
}
