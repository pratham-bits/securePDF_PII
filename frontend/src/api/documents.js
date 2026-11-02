import { api } from './client.js'

export const documents = {
  list: () => api.get('/documents'),
  get: (id) => api.get(`/documents/${id}`),
  findings: (id) => api.get(`/documents/${id}/findings`),
  upload: (file) => api.upload('/documents', file),
  analyze: (id) => api.post(`/documents/${id}/analyze`),
  remove: (id) => api.delete(`/documents/${id}`),
  setDecision: (id, findingId, decision, confirmOverride = false) =>
    api.patch(`/documents/${id}/findings/${findingId}`, {
      decision,
      confirm_override: confirmOverride,
    }),
  addBox: (id, box) => api.post(`/documents/${id}/findings`, box),
  removeBox: (id, findingId) => api.delete(`/documents/${id}/findings/${findingId}`),
}