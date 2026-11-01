import { api } from './client.js'

export const documents = {
  list: () => api.get('/documents'),
  get: (id) => api.get(`/documents/${id}`),
  upload: (file) => api.upload('/documents', file),
  analyze: (id) => api.post(`/documents/${id}/analyze`),
  remove: (id) => api.delete(`/documents/${id}`),
}