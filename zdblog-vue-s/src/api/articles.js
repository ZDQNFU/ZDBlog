import api from './index'

const BASE = '/articles/s/articles'

export function fetchArticles(params = {}) {
  return api.get(`${BASE}/`, { params })
}

export function fetchArticle(id) {
  return api.get(`${BASE}/${id}/`)
}

export function createArticle(data) {
  return api.post(`${BASE}/`, data)
}

export function generateArticleSummary(data) {
  return api.post(`${BASE}/generate-summary/`, data)
}

export function updateArticle(id, data) {
  return api.patch(`${BASE}/${id}/`, data)
}

export function deleteArticle(id) {
  return api.delete(`${BASE}/${id}/`)
}

export function uploadImage(file, articleId = '') {
  const formData = new FormData()
  formData.append('image', file)
  if (articleId) formData.append('article_id', articleId)
  return api.post('/articles/s/upload-image/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
