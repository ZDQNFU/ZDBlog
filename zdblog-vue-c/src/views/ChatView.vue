<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { streamChat, fetchChatHistory } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { marked } from 'marked'
import EmojiPicker from '@/components/EmojiPicker.vue'

marked.setOptions({ breaks: true, gfm: true })

const router = useRouter()
const auth = useAuthStore()

const messages = ref([])
const inputText = ref('')
const sending = ref(false)
const chatContainer = ref(null)
const loadingHistory = ref(false)
const showEmoji = ref(false)
const inputRef = ref(null)

const suggestions = [
  '最近有什么新文章？',
  '今天天气怎么样？',
  '给我讲个笑话',
  '介绍一下你自己',
]

function getTimeLabel(index) {
  const curr = new Date(messages.value[index].createdAt)
  if (!curr.getTime()) return null

  const fmt = (d, withDate) => {
    const hh = String(d.getHours()).padStart(2, '0')
    const mm = String(d.getMinutes()).padStart(2, '0')
    if (withDate) {
      const M = d.getMonth() + 1
      const D = d.getDate()
      return `${M}月${D}日 ${hh}:${mm}`
    }
    return `${hh}:${mm}`
  }

  if (index === 0) return fmt(curr, true)

  const prev = new Date(messages.value[index - 1].createdAt)
  if (!prev.getTime()) return null

  const diff = curr - prev
  if (diff < 5 * 60 * 1000) return null

  const sameDay = prev.toDateString() === curr.toDateString()
  return fmt(curr, !sameDay)
}

function renderMarkdown(text) {
  if (!text) return ''
  // 只去除末尾换行，保留段落间的 \n\n 让 marked 生成 <p> 标签
  return marked(text.trimEnd())
}

function getUserInitial() {
  return auth.user?.username?.charAt(0)?.toUpperCase() || '?'
}

function addMessage(role, content) {
  messages.value.push({ role, content, id: Date.now(), createdAt: new Date().toISOString() })
}

async function scrollToBottom() {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

function handleSuggestionClick(text) {
  inputText.value = text
  handleSend()
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || sending.value) return

  addMessage('user', text)
  inputText.value = ''
  await scrollToBottom()

  sending.value = true
  const aiId = Date.now()
  messages.value.push({ role: 'ai', content: '', id: aiId, createdAt: new Date().toISOString() })

  streamChat(
    text,
    (token) => {
      const msg = messages.value.find(m => m.id === aiId)
      if (msg) msg.content += token
      scrollToBottom()
    },
    () => {
      const msg = messages.value.find(m => m.id === aiId)
      if (msg) {
        msg.content = msg.content.trimEnd()
        msg.createdAt = new Date().toISOString()
      }
      sending.value = false
    },
    (err) => {
      const msg = messages.value.find(m => m.id === aiId)
      if (msg) msg.content = `[错误] ${err.message}`
      sending.value = false
      ElMessage.error(err.message || '对话失败')
    }
  )
}

function handleKeydown(e) {
  if (e.key === 'Enter') {
    e.preventDefault()
    handleSend()
  }
}

function insertEmoji(emoji) {
  const el = inputRef.value
  if (el) {
    const start = el.selectionStart
    const end = el.selectionEnd
    inputText.value = inputText.value.slice(0, start) + emoji + inputText.value.slice(end)
    setTimeout(() => {
      el.selectionStart = el.selectionEnd = start + emoji.length
      el.focus()
    }, 0)
  } else {
    inputText.value += emoji
  }
  showEmoji.value = false
}

async function loadHistory() {
  if (!auth.isAuthenticated) {
    addMessage('ai', '哼！又来了个烦人的家伙……本小姐今天心情还行，有什么话快说！')
    return
  }
  loadingHistory.value = true
  try {
    const data = await fetchChatHistory()
    if (data.messages?.length) {
      messages.value = data.messages.map((m, i) => ({ ...m, id: i }))
    } else {
      addMessage('ai', '哼！又来了个烦人的家伙……本小姐今天心情还行，有什么话快说！')
    }
  } catch {
    addMessage('ai', '哼！又来了个烦人的家伙……本小姐今天心情还行，有什么话快说！')
  } finally {
    loadingHistory.value = false
  }
}

const showWelcome = ref(false)

onMounted(async () => {
  await loadHistory()
  await nextTick()
  scrollToBottom()
  showWelcome.value = true
})
</script>

<template>
  <div class="chat-page">
    <!-- Header -->
    <header class="chat-header">
      <el-button :icon="ArrowLeft" text class="back-btn" @click="router.push('/')">返回</el-button>
      <div class="header-avatar">
        <div class="asuka-avatar">
          <span class="asuka-emoji">Asuka</span>
        </div>
        <div class="header-info">
          <span class="header-name">明日香</span>
          <span class="header-status">
            <span class="status-dot"></span>
            在线
          </span>
        </div>
      </div>
    </header>

    <!-- Messages -->
    <div class="chat-body" ref="chatContainer">
      <!-- Loading -->
      <div v-if="loadingHistory" class="loading-state">
        <div class="loading-dots">
          <span></span><span></span><span></span>
        </div>
      </div>

      <!-- Welcome -->
      <div v-if="!loadingHistory && messages.length <= 1" class="welcome-card">
        <div class="welcome-art">Asuka</div>
        <h3>明日香 · 聊天</h3>
        <p>我是惣流·明日香·兰格雷，EVA 二号机驾驶员。</p>
        <p>有什么想问的就快说吧，别浪费本小姐的时间！</p>
      </div>

      <!-- Messages -->
      <template v-else>
        <TransitionGroup name="msg">
          <template v-for="(m, idx) in messages" :key="m.id">
            <!-- Time divider (WeChat style) -->
            <div v-if="getTimeLabel(idx)" class="time-divider">
              <span>{{ getTimeLabel(idx) }}</span>
            </div>
            <div :class="['message-row', m.role]">
              <!-- AI Avatar -->
              <div v-if="m.role === 'ai'" class="msg-avatar ai-avatar">Asuka</div>

              <div class="msg-body">
                <div class="msg-meta">
                  <span class="msg-author">{{ m.role === 'ai' ? '明日香' : (auth.user?.username || '我') }}</span>
                </div>
                <div :class="['msg-bubble', m.role]">
                  <template v-if="m.role === 'user'"><span class="plain-text">{{ m.content }}</span></template>
                  <template v-else-if="m.role === 'ai' && sending && m === messages[messages.length - 1]">
                    <template v-if="m.content"><span class="plain-text">{{ m.content }}</span></template>
                    <div v-else class="typing-dots-inline">
                      <span></span><span></span><span></span>
                    </div>
                  </template>
                  <div v-else class="markdown-body" v-html="renderMarkdown(m.content)"></div>
                </div>
              </div>

              <!-- User Avatar -->
              <div v-if="m.role === 'user'" class="msg-avatar user-avatar">
                {{ getUserInitial() }}
              </div>
            </div>
          </template>
        </TransitionGroup>
      </template>

    </div>

    <!-- Quick suggestions -->
    <div v-if="messages.length <= 1 && !loadingHistory" class="quick-suggestions">
      <button
        v-for="s in suggestions"
        :key="s"
        class="suggestion-chip"
        @click="handleSuggestionClick(s)"
      >{{ s }}</button>
    </div>

    <!-- Input area (message-board style) -->
    <div class="chat-input-area">
      <button class="emoji-toggle-btn" @click="showEmoji = !showEmoji">😀</button>
      <input
        ref="inputRef"
        v-model="inputText"
        class="chat-msg-input"
        maxlength="500"
        placeholder="输入消息，Enter 发送..."
        :disabled="sending"
        @keydown.enter="handleKeydown"
      />
      <button class="send-btn" :disabled="!inputText.trim() || sending" @click="handleSend">发送</button>
    </div>

    <EmojiPicker :visible="showEmoji" @select="insertEmoji" @close="showEmoji = false" />
  </div>
</template>

<style scoped>
/* ========== Layout ========== */
.chat-page {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  background: var(--color-bg);
  z-index: 50;
  overflow: hidden;
}

/* ========== Header ========== */
.chat-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
  height: 60px;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
  backdrop-filter: blur(12px);
}
.back-btn {
  flex-shrink: 0;
}
.header-avatar {
  display: flex;
  align-items: center;
  gap: 10px;
}
.asuka-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--chat-accent), #f59e0b);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  box-shadow: 0 2px 8px rgba(212, 61, 61, 0.3);
}
.asuka-emoji {
  line-height: 1;
}
.header-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.header-name {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-text);
}
.header-status {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  gap: 5px;
}
.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #22c55e;
  animation: pulse-dot 2s ease-in-out infinite;
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

/* ========== Body ========== */
.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 20px 8px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  scroll-behavior: smooth;
}

/* ========== Loading ========== */
.loading-state {
  display: flex;
  justify-content: center;
  padding: 40px;
}
.loading-dots {
  display: flex;
  gap: 6px;
}
.loading-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--chat-accent);
  animation: bounce-dot 1.2s ease-in-out infinite;
}
.loading-dots span:nth-child(2) { animation-delay: 0.15s; }
.loading-dots span:nth-child(3) { animation-delay: 0.3s; }
@keyframes bounce-dot {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
  40% { transform: translateY(-10px); opacity: 1; }
}

/* ========== Welcome ========== */
.welcome-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  margin: auto;
  text-align: center;
  animation: welcome-in 0.6s ease-out;
}
.welcome-art {
  font-size: 4rem;
  margin-bottom: 16px;
  animation: float 3s ease-in-out infinite;
}
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}
.welcome-card h3 {
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--chat-accent);
  margin-bottom: 12px;
}
.welcome-card p {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  line-height: 1.7;
}
@keyframes welcome-in {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ========== Time divider (WeChat style) ========== */
.time-divider {
  display: flex;
  justify-content: center;
  padding: 4px 0;
  margin: -8px 0;
}
.time-divider span {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  padding: 2px 12px;
  border-radius: 4px;
  opacity: 0.8;
}

/* ========== Message rows ========== */
.message-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  max-width: 88%;
  animation: msg-in 0.35s ease-out;
}
.message-row.user {
  align-self: flex-end;
  justify-content: flex-end;
}
.message-row.ai {
  align-self: flex-start;
}
@keyframes msg-in {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ========== Avatars ========== */
.msg-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 0.8rem;
  font-weight: 700;
  align-self: flex-start;
}
.ai-avatar {
  background: linear-gradient(135deg, var(--chat-accent), #f59e0b);
  color: #fff;
  font-size: 1rem;
  line-height: 1;
  box-shadow: 0 2px 6px rgba(212, 61, 61, 0.25);
}
.user-avatar {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  box-shadow: 0 2px 6px rgba(99, 102, 241, 0.25);
}

/* ========== Message body ========== */
.msg-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.msg-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 4px;
}
.message-row.user .msg-meta {
  justify-content: flex-end;
}
.msg-author {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--color-text-secondary);
}

/* ========== Bubbles ========== */
.msg-bubble {
  padding: 10px 16px;
  border-radius: 16px;
  font-size: 0.9rem;
  line-height: 1.7;
  word-break: break-word;
  position: relative;
}
.msg-bubble.user {
  background: linear-gradient(135deg, var(--chat-accent), #e05a5a);
  color: #fff;
  border-bottom-right-radius: 6px;
  box-shadow: 0 2px 10px rgba(212, 61, 61, 0.2);
}
.msg-bubble.ai {
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-bottom-left-radius: 6px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

/* 纯文本（用户消息 & 流式输出中的 AI 消息，参照 S 端 pre-wrap） */
.plain-text {
  white-space: pre-wrap;
}

/* ========== Markdown in AI bubbles ========== */
.markdown-body :deep(p) {
  margin: 0 0 8px;
}
.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}
.markdown-body :deep(code) {
  background: var(--color-bg);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.85em;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
}
.markdown-body :deep(pre) {
  background: #1e293b;
  color: #e2e8f0;
  padding: 14px 16px;
  border-radius: 10px;
  overflow-x: auto;
  margin: 8px 0;
  font-size: 0.83em;
  line-height: 1.5;
}
.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
  color: inherit;
  font-size: inherit;
}
.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 20px;
  margin: 4px 0;
}
.markdown-body :deep(li) {
  margin: 2px 0;
}
.markdown-body :deep(blockquote) {
  border-left: 3px solid var(--chat-accent);
  padding-left: 12px;
  margin: 8px 0;
  color: var(--color-text-secondary);
}
.markdown-body :deep(a) {
  color: var(--chat-accent);
  text-decoration: underline;
}
.markdown-body :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
  width: 100%;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid var(--color-border);
  padding: 6px 10px;
  font-size: 0.83em;
}
.markdown-body :deep(th) {
  background: var(--color-bg);
}

/* ========== Typing dots (inline in AI bubble) ========== */
.typing-dots-inline {
  display: flex;
  gap: 5px;
  padding: 4px 2px;
}
.typing-dots-inline span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--chat-accent);
  animation: typing-bounce 1.2s ease-in-out infinite;
}
.typing-dots-inline span:nth-child(2) { animation-delay: 0.15s; }
.typing-dots-inline span:nth-child(3) { animation-delay: 0.3s; }
@keyframes typing-bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-8px); opacity: 1; }
}

/* ========== Quick suggestions ========== */
.quick-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 20px 4px;
  flex-shrink: 0;
}
.suggestion-chip {
  padding: 6px 14px;
  font-size: 0.82rem;
  border: 1px solid var(--color-border);
  border-radius: 20px;
  background: var(--color-surface);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}
.suggestion-chip:hover {
  border-color: var(--chat-accent);
  color: var(--chat-accent);
  background: var(--chat-accent-light);
}

/* ========== Input area (message-board style) ========== */
.chat-input-area {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  flex-shrink: 0;
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
}

.emoji-toggle-btn {
  width: 42px;
  height: 42px;
  border: none;
  border-radius: 12px;
  background: var(--color-bg);
  font-size: 20px;
  cursor: pointer;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chat-msg-input {
  flex: 1;
  height: 42px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 0 14px;
  font-size: 15px;
  outline: none;
  background: var(--color-bg);
  color: var(--color-text);
  font-family: inherit;
}
.chat-msg-input:focus {
  border-color: var(--chat-accent);
}

.send-btn {
  height: 42px;
  padding: 0 20px;
  border: none;
  border-radius: 12px;
  background: var(--chat-accent);
  color: #fff;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.18s;
  flex-shrink: 0;
  font-size: 0.9rem;
  font-family: inherit;
}
.send-btn:hover:not(:disabled) {
  opacity: 0.9;
}
.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ========== TransitionGroup ========== */
.msg-enter-active {
  transition: all 0.35s ease-out;
}
.msg-enter-from {
  opacity: 0;
  transform: translateY(16px);
}
.msg-leave-active {
  transition: all 0.2s ease-in;
}
.msg-leave-to {
  opacity: 0;
  transform: scale(0.95);
}

/* ========== Responsive ========== */
@media (max-width: 640px) {
  .chat-body {
    padding: 12px 12px 4px;
  }
  .chat-input-area {
    padding: 8px 12px;
    gap: 6px;
  }
  .message-row {
    max-width: 94%;
  }
  .quick-suggestions {
    padding: 6px 12px 2px;
  }
}
</style>
