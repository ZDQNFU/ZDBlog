import api from './index'

const BASE = '/articles/s/comments'

export function fetchComments(params = {}) {
  return api.get(`${BASE}/`, { params })
}

export function updateComment(id, data) {
  return api.patch(`${BASE}/${id}/`, data)
}

export function fetchComment(id) {
  return api.get(`${BASE}/${id}/`)
}

export function deleteComment(id) {
  return api.delete(`${BASE}/${id}/`)
}

const KEYWORDS_BASE = '/articles/s/comment-keywords'

export function fetchCommentKeywords(params = {}) {
  return api.get(`${KEYWORDS_BASE}/`, { params })
}

export function createCommentKeyword(data) {
  return api.post(`${KEYWORDS_BASE}/`, data)
}

export function updateCommentKeyword(id, data) {
  return api.patch(`${KEYWORDS_BASE}/${id}/`, data)
}

export function deleteCommentKeyword(id) {
  return api.delete(`${KEYWORDS_BASE}/${id}/`)
}
