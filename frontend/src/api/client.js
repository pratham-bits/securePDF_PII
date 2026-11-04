export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

let onUnauthorized = null

// The auth provider registers this so an expired session logs the user out everywhere.
export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler
}

// FastAPI sends {detail: "text"} or, for validation, {detail: [{msg: "..."}]}.
function messageFrom(data, status) {
  const detail = data && data.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((item) => item.msg).join('; ')
  }
  return `Request failed (${status})`
}

async function request(path, { method = 'GET', json, body, as = 'json' } = {}) {
  const options = { method, credentials: 'include', headers: {} }
  if (json !== undefined) {
    options.headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(json)
  } else if (body !== undefined) {
    options.body = body // FormData: the browser sets the multipart header itself
  }

  let response
  try {
    response = await fetch(`/api${path}`, options)
  } catch {
    throw new ApiError(0, 'Cannot reach the server. Is it running?')
  }

  // A 401 on anything except the auth calls means the session has expired.
  if (response.status === 401 && !path.startsWith('/auth/') && onUnauthorized) {
    onUnauthorized()
  }

  if (!response.ok) {
    const contentType = response.headers.get('content-type') || ''
    const data = contentType.includes('application/json') ? await response.json() : null
    throw new ApiError(response.status, messageFrom(data, response.status))
  }

  if (response.status === 204) return null
  if (as === 'blob') return response.blob()
  return response.json()
}

export const api = {
  get: (path) => request(path),
  post: (path, json) => request(path, { method: 'POST', json }),
  patch: (path, json) => request(path, { method: 'PATCH', json }),
  delete: (path) => request(path, { method: 'DELETE' }),
  download: (path) => request(path, { as: 'blob' }),
  upload: (path, file) => {
    const form = new FormData()
    form.append('file', file)
    return request(path, { method: 'POST', body: form })
  },
}