import api from './index'

const BASE = '/moments/s/moments'
export function fetchMoments(params = {}) { return api.get(`${BASE}/`, { params }) }
export function createMoment(data) { return api.post(`${BASE}/`, data) }
export function updateMoment(id, data) { return api.patch(`${BASE}/${id}/`, data) }
export function deleteMoment(id) { return api.delete(`${BASE}/${id}/`) }
