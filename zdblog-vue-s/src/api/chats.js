import api from './index'

const BASE = '/chat-robot'

export function fetchPersonas(params = {}) {
  return api.get(`${BASE}/manage/personas/`, { params })
}
export function fetchPersona(id) {
  return api.get(`${BASE}/manage/personas/${id}/`)
}
export function createPersona(data) {
  return api.post(`${BASE}/manage/personas/`, data)
}
export function updatePersona(id, data) {
  return api.patch(`${BASE}/manage/personas/${id}/`, data)
}
export function deletePersona(id) {
  return api.delete(`${BASE}/manage/personas/${id}/`)
}

export function fetchChatUsers(params = {}) {
  return api.get(`${BASE}/users/`, { params })
}

export function fetchChatUserDetail(userId, params = {}) {
  return api.get(`${BASE}/users/${userId}/`, { params })
}

export function clearChatHistory(userId) {
  return api.post(`${BASE}/users/${userId}/clear/`)
}

export function trimChatHistory(userId, days) {
  return api.post(`${BASE}/users/${userId}/trim/`, { days })
}
