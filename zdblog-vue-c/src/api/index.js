const ARTICLES_BASE = '/api/articles/c'
const AUTH_BASE = '/api/auth'

async function request(url, options = {}) {
  const token = localStorage.getItem('access_token')
  const headers = { ...options.headers }
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  const res = await fetch(url, { ...options, headers })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const msg = body.detail || Object.values(body).flat().join('; ') || `请求失败: ${res.status}`
    throw new Error(msg)
  }
  return res.status === 204 ? null : res.json()
}

// ==================== Articles ====================

export function fetchArticleList(page = 1, pageSize = 10, search = '') {
  let url = `${ARTICLES_BASE}/list/?page=${page}&page_size=${pageSize}`
  if (search) {
    url += `&search=${encodeURIComponent(search)}`
  }
  return request(url)
}

export function fetchArticleDetail(id) {
  return request(`${ARTICLES_BASE}/${id}/`)
}

// ==================== Comments ====================

export function createComment(article, content, parent = null) {
  return request(`${ARTICLES_BASE}/comments/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ article, content, parent }),
  })
}

// ==================== Auth ====================

export function fetchCaptcha() {
  return request(`${AUTH_BASE}/captcha/`)
}

export function login(data) {
  return request(`${AUTH_BASE}/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export function register(data) {
  return request(`${AUTH_BASE}/register/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export function sendVerificationCode(email) {
  return request(`${AUTH_BASE}/send-code/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
}

export function fetchUserInfo() {
  return request(`${AUTH_BASE}/me/`)
}

// ==================== Likes ====================

export function likeArticle(id) {
  return request(`${ARTICLES_BASE}/${id}/like/`, { method: 'POST' })
}

export function unlikeArticle(id) {
  return request(`${ARTICLES_BASE}/${id}/like/`, { method: 'DELETE' })
}

export function verifyArticlePassword(id, password) {
  return request(`${ARTICLES_BASE}/${id}/verify/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  })
}

// ==================== Chat (SSE) ====================

const CHAT_BASE = '/api/chat-robot'

export async function streamChat(conversationId, message, onToken, { signal } = {}) {
  const token = localStorage.getItem('access_token')
  const res = await fetch(`${CHAT_BASE}/stream/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ conversation_id: conversationId, message }),
    signal,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `请求失败: ${res.status}`)
  }
  if (!res.body) throw new Error('浏览器不支持流式回复')
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finished = false
  try {
    while (!finished) {
      const { done, value } = await reader.read()
      if (done) throw new Error('回复连接已中断，请重试')
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6))
          if (data.error) throw new Error(data.error)
          if (data.done) {
            finished = true
            break
          }
          if (typeof data.token === 'string') onToken(data.token)
        }
      }
    }
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}

// ==================== Chat History ====================

export function fetchChatHistory(conversationId) {
  return request(`${CHAT_BASE}/history/?conversation_id=${encodeURIComponent(conversationId)}`)
}

export function fetchChatPersonas() {
  return request(`${CHAT_BASE}/personas/`)
}
export function fetchChatConversations() {
  return request(`${CHAT_BASE}/conversations/`)
}
export function fetchChatConversation(id) {
  return request(`${CHAT_BASE}/conversations/${id}/`)
}
export function createChatConversation(personaId) {
  return request(`${CHAT_BASE}/conversations/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ persona_id: personaId }),
  })
}
export function renameChatConversation(id, title) {
  return request(`${CHAT_BASE}/conversations/${id}/`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
}
export function deleteChatConversation(id) {
  return request(`${CHAT_BASE}/conversations/${id}/`, { method: 'DELETE' })
}

// ==================== Tags ====================

export function fetchTags() {
  return request(`${ARTICLES_BASE}/tags/`)
}

export function fetchRandomArticles() {
  return request(`${ARTICLES_BASE}/random/`)
}

const MESSAGE_BASE = '/api/messages/c'

export function fetchMessages() {
  return request(`${MESSAGE_BASE}/list/`)
}

export function createMessage(content) {
  return request(`${MESSAGE_BASE}/create/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  })
}

export function likeMessage(id) {
  return request(`${MESSAGE_BASE}/${id}/like/`, { method: 'POST' })
}

export function unlikeMessage(id) {
  return request(`${MESSAGE_BASE}/${id}/like/`, { method: 'DELETE' })
}

// ==================== Links ====================

const LINKS_BASE = '/api/links/c/links'

export function fetchLinks() {
  return request(`${LINKS_BASE}/`)
}

// ==================== System Config ====================

const SYSTEM_CONFIG_BASE = '/api/system-config'

// 公开只读配置（目前是页脚备案号），未配置时后端返回空字符串
export function fetchPublicConfig() {
  return request(`${SYSTEM_CONFIG_BASE}/c/public/`)
}
