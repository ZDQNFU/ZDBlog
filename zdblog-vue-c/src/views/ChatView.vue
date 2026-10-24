<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import {
  streamChat,
  fetchChatPersonas,
  fetchChatConversations,
  createChatConversation,
  fetchChatConversation,
  renameChatConversation,
  deleteChatConversation,
} from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useTheme } from '@/composables/useTheme'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import { safeMarkdown } from '@/utils/chatMarkdown'
import EmojiPicker from '@/components/EmojiPicker.vue'
import '@/assets/messageComposer.css'
marked.setOptions({ breaks: true, gfm: true })
const router = useRouter()
const auth = useAuthStore()
const { isDark, toggle: toggleTheme } = useTheme()
const conversations = ref([]),
  personas = ref([]),
  selectedPersona = ref(''),
  current = ref(null)
const messages = ref([]),
  inputText = ref(''),
  messageInput = ref(null),
  showEmoji = ref(false),
  sending = ref(false),
  loading = ref(true),
  ready = ref(false)
const sidebarOpen = ref(false),
  chatContainer = ref(null),
  search = ref('')
let controller = null,
  loadVersion = 0,
  disposed = false
const persona = computed(() => personas.value.find((p) => p.id === selectedPersona.value))
const speaker = computed(() => current.value?.persona_name || persona.value?.name || 'AI 助手')
const filteredConversations = computed(() =>
  conversations.value.filter((c) => c.title.toLowerCase().includes(search.value.toLowerCase())),
)
const hasChatAccess = computed(() => auth.user?.is_staff || auth.user?.is_superuser)
const canSend = computed(
  () =>
    ready.value &&
    hasChatAccess.value &&
    !loading.value &&
    !sending.value &&
    !!inputText.value.trim() &&
    (!!current.value || !!selectedPersona.value),
)
const suggestions = ['最近有什么新文章？', '今天天气怎么样？', '给我讲个笑话', '介绍一下你自己']
async function scrollToBottom() {
  await nextTick()
  if (chatContainer.value) chatContainer.value.scrollTop = chatContainer.value.scrollHeight
}
// 会话列表右侧的时间：今天显示时刻，昨天显示「昨天」，更早显示日期
function formatTime(value) {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  const now = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  if (d.toDateString() === now.toDateString()) return `${pad(d.getHours())}:${pad(d.getMinutes())}`
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  if (d.toDateString() === yesterday.toDateString()) return '昨天'
  const md = `${d.getMonth() + 1}/${d.getDate()}`
  return d.getFullYear() === now.getFullYear() ? md : `${d.getFullYear()}/${md}`
}
async function refreshConversations() {
  const data = await fetchChatConversations()
  if (!disposed) conversations.value = data.conversations
}
function newChat() {
  if (sending.value) return
  loadVersion++
  current.value = null
  messages.value = []
  inputText.value = ''
  showEmoji.value = false
  loading.value = false
  sidebarOpen.value = false
}
async function openConversation(c) {
  if (sending.value) return
  const version = ++loadVersion
  loading.value = true
  sidebarOpen.value = false
  try {
    const data = await fetchChatConversation(c.id)
    if (version !== loadVersion || disposed) return
    current.value = data.conversation
    messages.value = data.messages
    inputText.value = ''
    await scrollToBottom()
  } catch (e) {
    if (version === loadVersion) ElMessage.error(e.message)
  } finally {
    if (version === loadVersion) loading.value = false
  }
}
async function renameConversation(c) {
  if (sending.value) return
  try {
    const { value } = await ElMessageBox.prompt('输入聊天名称', '重命名', {
      inputValue: c.title,
      inputValidator: (v) => (!!v?.trim() && v.trim().length <= 100) || '请输入 1 到 100 个字符',
    })
    const updated = await renameChatConversation(c.id, value.trim())
    if (current.value?.id === c.id) current.value = updated
    await refreshConversations()
  } catch (e) {
    if (e instanceof Error) ElMessage.error(e.message)
  }
}
async function removeConversation(c) {
  if (sending.value) return
  try {
    await ElMessageBox.confirm(`删除「${c.title}」及其全部消息？`, '删除聊天', { type: 'warning' })
    await deleteChatConversation(c.id)
    if (current.value?.id === c.id) newChat()
    await refreshConversations()
  } catch (e) {
    if (e instanceof Error) ElMessage.error(e.message)
  }
}
async function handleSend() {
  if (!canSend.value) return
  showEmoji.value = false
  const text = inputText.value.trim()
  sending.value = true
  try {
    if (!current.value) {
      current.value = await createChatConversation(selectedPersona.value)
      conversations.value.unshift(current.value)
    }
    inputText.value = ''
    const aiId = `ai-${Date.now()}`
    messages.value.push(
      { id: `user-${Date.now()}`, role: 'user', content: text },
      { id: aiId, role: 'ai', content: '' },
    )
    controller = new AbortController()
    await scrollToBottom()
    await streamChat(
      current.value.id,
      text,
      (token) => {
        const target = messages.value.find((m) => m.id === aiId)
        if (target) target.content += token
        scrollToBottom()
      },
      { signal: controller.signal },
    )
  } catch (e) {
    if (e.name !== 'AbortError') ElMessage.error(e.message || '对话失败')
  } finally {
    controller = null
    if (!disposed && current.value) {
      try {
        const data = await fetchChatConversation(current.value.id)
        current.value = data.conversation
        messages.value = data.messages
        await refreshConversations()
        await scrollToBottom()
      } catch (e) {
        ElMessage.error(e.message)
      }
    }
    sending.value = false
  }
}
function suggestion(text) {
  inputText.value = text
  handleSend()
}
async function insertEmoji(emoji) {
  const input = messageInput.value
  const start = input?.selectionStart ?? inputText.value.length
  const end = input?.selectionEnd ?? start
  if (inputText.value.length - (end - start) + emoji.length > 10000) return
  inputText.value = inputText.value.slice(0, start) + emoji + inputText.value.slice(end)
  showEmoji.value = false
  await nextTick()
  input?.focus()
  input?.setSelectionRange(start + emoji.length, start + emoji.length)
}
function keydown(e) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    handleSend()
  }
}
onMounted(async () => {
  try {
    const [roles, data] = await Promise.all([fetchChatPersonas(), fetchChatConversations()])
    if (disposed) return
    personas.value = roles
    selectedPersona.value = roles[0]?.id || ''
    conversations.value = data.conversations
    ready.value = true
    if (conversations.value.length) await openConversation(conversations.value[0])
  } catch (e) {
    ElMessage.error(`加载聊天失败：${e.message}`)
  } finally {
    loading.value = false
  }
})
onBeforeUnmount(() => {
  disposed = true
  loadVersion++
  controller?.abort()
})
</script>

<template>
  <div class="chat-page" :class="{ 'is-dark': isDark }">
    <button
      v-if="sidebarOpen"
      class="sidebar-mask"
      aria-label="关闭聊天列表"
      @click="sidebarOpen = false"
    ></button>
    <aside :class="['chat-sidebar', { open: sidebarOpen }]">
      <a class="brand" href="/" @click.prevent="router.push('/')">← ZDBLOG <span>AI</span></a>
      <button class="new-chat" :disabled="sending || !ready" @click="newChat">＋ 新建聊天</button>
      <input v-model="search" class="chat-search" aria-label="搜索聊天" placeholder="搜索聊天…" />
      <div class="session-list">
        <div
          v-for="c in filteredConversations"
          :key="c.id"
          :class="['session', { active: current?.id === c.id }]"
        >
          <button class="session-main" :disabled="sending" @click="openConversation(c)">
            <span class="session-title">{{ c.title }}</span
            ><span class="session-meta"
              ><small>{{ c.persona_name }}</small
              ><time>{{ formatTime(c.updated_at) }}</time></span
            >
          </button>
          <div class="session-actions">
            <button
              :disabled="sending"
              title="重命名聊天"
              :aria-label="`重命名 ${c.title}`"
              @click="renameConversation(c)"
            >
              ✎</button
            ><button
              :disabled="sending"
              title="删除聊天"
              :aria-label="`删除 ${c.title}`"
              @click="removeConversation(c)"
            >
              ×
            </button>
          </div>
        </div>
        <p v-if="ready && !conversations.length" class="sidebar-empty">你的聊天会保存在这里</p>
      </div>
      <div class="sidebar-footer">{{ auth.user?.username }} · 独立会话记忆</div>
    </aside>
    <main class="chat-main">
      <header class="chat-header">
        <button class="menu-toggle" aria-label="打开聊天列表" @click="sidebarOpen = !sidebarOpen">
          ☰
        </button>
        <div class="chat-heading">
          <strong>{{ current?.title || '新聊天' }}</strong
          ><span class="header-role">{{ speaker }}</span>
        </div>
        <div class="header-actions">
          <span v-if="sending" class="generation-status">正在回复…</span>
          <button
            class="chat-theme-toggle"
            :aria-label="isDark ? '切换亮色模式' : '切换暗色模式'"
            :title="isDark ? '切换亮色模式' : '切换暗色模式'"
            :aria-pressed="isDark"
            @click="toggleTheme"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <template v-if="isDark">
                <circle cx="12" cy="12" r="4" />
                <path
                  d="M12 2v2m0 16v2M2 12h2m16 0h2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42"
                />
              </template>
              <path v-else d="M20.9 13A9 9 0 0 1 11 3.1 9 9 0 1 0 20.9 13Z" />
            </svg>
          </button>
        </div>
      </header>
      <div ref="chatContainer" class="chat-body" :aria-busy="loading">
        <p v-if="loading" class="loading-state">正在加载聊天…</p>
        <div v-else-if="!messages.length" class="welcome-card">
          <div class="welcome-symbol">✦</div>
          <h1>今天想聊点什么？</h1>
          <template v-if="!current"
            ><label for="persona">选择与你聊天的人物</label
            ><select id="persona" v-model="selectedPersona" :disabled="sending || !ready">
              <option v-for="p in personas" :key="p.id" :value="p.id">{{ p.name }}</option>
              <option v-if="!personas.length" value="">暂无可用人物，请联系管理员</option>
            </select>
            <p>{{ persona?.description }}</p></template
          >
          <div v-if="current?.greeting || persona?.greeting" class="greeting-row">
            <div class="message-avatar">{{ speaker.slice(0, 1) }}</div>
            <div class="bubble greeting">{{ current?.greeting || persona?.greeting }}</div>
          </div>
          <div class="suggestions">
            <button
              v-for="s in suggestions"
              :key="s"
              :disabled="sending || !hasChatAccess || !ready || loading"
              @click="suggestion(s)"
            >
              {{ s }} ↗
            </button>
          </div>
        </div>
        <div v-else class="message-list" aria-live="polite">
          <article v-for="m in messages" :key="m.id" :class="['message-row', m.role]">
            <div class="message-avatar">
              {{
                m.role === 'ai' ? speaker.slice(0, 1) : (auth.user?.username || '我').slice(0, 1)
              }}
            </div>
            <div class="message-content">
              <p v-if="m.role === 'user'" class="bubble user-text">{{ m.content }}</p>
              <div
                v-else-if="m.content"
                class="bubble markdown-body"
                v-html="safeMarkdown(marked.parse(m.content))"
              ></div>
              <span v-else-if="sending" class="bubble typing" role="status" aria-label="正在思考"
                ><i></i><i></i><i></i
              ></span>
              <span v-else class="failed-hint">未收到回复，请重试</span>
              <small v-if="m.role === 'ai' && m.content" class="ai-disclaimer">
                AI 生成的内容仅供参考
              </small>
            </div>
          </article>
        </div>
      </div>
      <div class="composer-wrap">
        <p v-if="!hasChatAccess" class="access-hint">当前聊天功能仅向管理员开放。</p>
        <div class="dm-input-bar">
          <button
            class="dm-emoji-btn"
            aria-label="选择表情"
            :aria-expanded="showEmoji"
            :disabled="sending || loading || !ready || !hasChatAccess"
            @click="showEmoji = !showEmoji"
          >
            😀
          </button>
          <textarea
            ref="messageInput"
            v-model="inputText"
            class="dm-msg-input"
            maxlength="10000"
            rows="1"
            placeholder="发送一条消息..."
            aria-label="聊天消息"
            title="Enter 发送，Shift+Enter 换行"
            :disabled="sending || loading || !ready || !hasChatAccess"
            @keydown="keydown"
          ></textarea>
          <button class="dm-send-btn" :disabled="!canSend" @click="handleSend">
            {{ sending ? '回复中' : '发送' }}
          </button>
        </div>
        <EmojiPicker :visible="showEmoji" @select="insertEmoji" @close="showEmoji = false" />
      </div>
    </main>
  </div>
</template>

<style scoped>
/* ══════════════════════════════════════════════════════════════════
   微信风格聊天界面
   会话栏沿用站点主题变量；聊天配色通过共享主题状态绑定到页面根节点。
   ══════════════════════════════════════════════════════════════════ */
.chat-page {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  background: transparent;
  color: var(--color-text);
  color-scheme: light;

  --wx-chat-bg: rgba(237, 237, 237, .9);
  --wx-bubble-other: #ffffff; /* 对方（AI）气泡 */
  --wx-bubble-self: #95ec69; /* 自己气泡：微信绿 */
  --wx-bubble-self-text: #101010;
  --wx-code-bg: #f2f3f5;
  --wx-action: #07c160; /* 微信界面绿：发送键 / 状态强调 */
  --wx-link: #067d3e;
  --wx-button-bg: #078546;
  --wx-button-text: #ffffff;
  --wx-avatar-text: #ffffff;
  --wx-scroll: #00000026;
  --wx-shadow: 0 1px 2px #0000000a;
  --wx-radius: 5px; /* 微信气泡接近直角，只有一点点圆 */
}
.chat-page.is-dark {
  color-scheme: dark;
  --wx-chat-bg: rgba(15, 23, 42, .9);
  --wx-bubble-other: #1e293b;
  --wx-bubble-self: #2f5f3e;
  --wx-bubble-self-text: #eaf5ec;
  --wx-code-bg: #0b1220;
  --wx-action: #4ade80;
  --wx-link: #6ee7a0;
  --wx-button-bg: #4ade80;
  --wx-button-text: #082516;
  --wx-avatar-text: #0b1220;
  --wx-scroll: #ffffff26;
  --wx-shadow: none;
}
button,
input,
textarea,
select {
  font: inherit;
}
button {
  cursor: pointer;
}
button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}
button:focus-visible,
select:focus-visible,
.markdown-body :deep(a:focus-visible) {
  outline: 2px solid var(--color-primary);
  outline-offset: 3px;
}
.chat-search::placeholder,
.dm-msg-input::placeholder {
  color: var(--color-text-secondary);
  opacity: 1;
}

/* ---------------- 左栏：会话列表 ---------------- */
.chat-sidebar {
  width: 264px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 20px 12px 12px;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
}
.brand {
  padding: 0 8px;
  font-size: 16px;
  font-weight: 750;
  letter-spacing: 1px;
  color: inherit;
  text-decoration: none;
}
.brand span {
  color: var(--color-primary);
}
.new-chat {
  padding: 10px 12px;
  border: 1px solid color-mix(in srgb, var(--color-primary) 28%, transparent);
  border-radius: 8px;
  background: color-mix(in srgb, var(--color-primary) 10%, transparent);
  color: var(--color-primary);
  text-align: center;
  font-size: 14px;
  font-weight: 600;
}
.new-chat:hover:not(:disabled) {
  background: color-mix(in srgb, var(--color-primary) 18%, transparent);
}
.chat-search {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 12px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: var(--color-bg);
  color: inherit;
  font-size: 13px;
  outline: none;
}
.chat-search:focus {
  border-color: var(--color-primary);
}
.session-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--wx-scroll) transparent;
}
.session {
  display: flex;
  align-items: center;
  margin-bottom: 2px;
  border-radius: 6px;
}
.session.active {
  background: color-mix(in srgb, var(--color-primary) 12%, transparent);
}
.session:hover:not(.active) {
  background: var(--color-bg);
}
.session-main {
  flex: 1;
  min-width: 0;
  padding: 10px;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
}
.session-title {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}
.session.active .session-title {
  font-weight: 600;
}
.session-meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-top: 4px;
  font-size: 11px;
  color: var(--color-text-secondary);
}
.session-meta small,
.session-meta time {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-meta time {
  flex-shrink: 0;
}
/* 重命名 / 删除：平时收起，悬停或选中时才出现，且触摸屏常显 */
.session-actions {
  display: flex;
  padding-right: 4px;
  opacity: 0;
  transition: opacity 0.15s;
}
.session:hover .session-actions,
.session.active .session-actions {
  opacity: 1;
}
.session-actions button {
  padding: 4px 5px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 16px;
  line-height: 1;
}
.session-actions button:hover {
  background: var(--color-bg);
  color: var(--color-text);
}
.session-actions button:last-child:hover {
  color: #e5484d;
}
.sidebar-empty,
.sidebar-footer {
  padding: 10px;
  color: var(--color-text-secondary);
  font-size: 12px;
}
.sidebar-footer {
  border-top: 1px solid var(--color-border);
}

/* ---------------- 右侧：聊天区 ---------------- */
.chat-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--wx-chat-bg);
}
.chat-header {
  flex-shrink: 0;
  height: 58px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}
.chat-heading {
  flex: 1;
  min-width: 0;
}
.chat-header strong {
  display: block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 15px;
}
.header-role {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  color: var(--color-text-secondary);
}
.generation-status {
  font-size: 12px;
  color: var(--wx-link);
  white-space: nowrap;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}
.chat-theme-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg);
  color: var(--color-text);
}
.chat-theme-toggle:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.menu-toggle {
  display: none;
  border: 0;
  background: transparent;
  color: inherit;
  font-size: 22px;
}
.chat-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 20px 24px 4px;
  scrollbar-width: thin;
  scrollbar-color: var(--wx-scroll) transparent;
}
.chat-body::-webkit-scrollbar {
  width: 8px;
}
.chat-body::-webkit-scrollbar-thumb {
  border-radius: 4px;
  background: var(--wx-scroll);
}

/* ---- 空状态 ---- */
.loading-state {
  padding-top: 40px;
  text-align: center;
  color: var(--color-text-secondary);
  font-size: 13px;
}
.welcome-card {
  max-width: 660px;
  margin: clamp(8px, 6vh, 64px) auto 0;
  text-align: center;
}
.welcome-symbol {
  width: 56px;
  height: 56px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  background: color-mix(in srgb, var(--color-primary) 12%, transparent);
  color: var(--color-primary);
  font-size: 26px;
}
.welcome-card h1 {
  margin: 16px 0 20px;
  font-size: clamp(20px, 2.4vw, 26px);
}
.welcome-card label {
  display: block;
  margin-bottom: 10px;
  font-size: 13px;
  color: var(--color-text-secondary);
}
.welcome-card select {
  padding: 9px 34px 9px 14px;
  max-width: 100%;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  color: inherit;
}
.welcome-card p {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.7;
}
/* 开场白直接摆成一条「收到的消息」，空状态就已经是微信的样子 */
.greeting-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 24px;
  text-align: left;
}
.greeting-row .bubble {
  flex: 1;
  max-width: none;
}
.greeting {
  white-space: pre-wrap;
}
.suggestions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 22px;
}
.suggestions button {
  padding: 12px 14px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  color: inherit;
  text-align: left;
  font-size: 13px;
  transition:
    border-color 0.15s,
    color 0.15s;
}
.suggestions button:hover:not(:disabled) {
  border-color: var(--wx-action);
  color: var(--wx-action);
}

/* ---- 消息列表 ---- */
.message-list {
  max-width: 860px;
  margin: 0 auto;
}
.message-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding-bottom: 18px;
}
/* 自己的消息整行翻过来：头像在右，气泡在左 */
.message-row.user {
  flex-direction: row-reverse;
}
.message-avatar {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  background: var(--color-primary);
  color: var(--wx-avatar-text);
  font-size: 16px;
  font-weight: 600;
  user-select: none;
}
.user .message-avatar {
  background: var(--wx-button-bg);
  color: var(--wx-button-text);
}
.message-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.user .message-content {
  align-items: flex-end;
}
/* 气泡公共样式 */
.bubble {
  position: relative;
  max-width: min(74%, 620px);
  padding: 9px 13px;
  border-radius: var(--wx-radius);
  background: var(--wx-bubble-other);
  color: var(--color-text);
  box-shadow: var(--wx-shadow);
  font-size: 15px;
  line-height: 1.65;
  overflow-wrap: anywhere;
}
/* 气泡尖角：一块 12×12 的透明边框盒子，只亮一侧边框 */
.bubble::after {
  content: '';
  position: absolute;
  top: 11px;
  width: 0;
  height: 0;
  border: 6px solid transparent;
}
.ai .bubble::after {
  left: -11px;
  border-right-color: var(--wx-bubble-other);
}
.user .bubble {
  background: var(--wx-bubble-self);
  color: var(--wx-bubble-self-text);
}
.user .bubble::after {
  right: -11px;
  border-left-color: var(--wx-bubble-self);
}
.greeting-row .bubble::after {
  left: -11px;
  border-right-color: var(--wx-bubble-other);
}
.user-text {
  margin: 0;
  white-space: pre-wrap;
}
/* 「正在思考」三个点 */
.typing {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 13px;
}
.typing i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-text-secondary);
  animation: wx-typing 1.2s infinite ease-in-out;
}
.typing i:nth-child(2) {
  animation-delay: 0.18s;
}
.typing i:nth-child(3) {
  animation-delay: 0.36s;
}
@keyframes wx-typing {
  0%,
  60%,
  100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  30% {
    opacity: 1;
    transform: translateY(-3px);
  }
}
.failed-hint {
  padding-top: 6px;
  font-size: 12px;
  color: var(--color-text-secondary);
}
/* Markdown 正文（AI 气泡内部） */
.markdown-body :deep(p) {
  margin: 0 0 10px;
}
.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 12px 0 8px;
  font-size: 1.05em;
}
.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 8px 0;
  padding-left: 22px;
}
.markdown-body :deep(pre) {
  margin: 10px 0;
  padding: 12px 14px;
  border: 0;
  border-radius: 6px;
  background: var(--wx-code-bg);
  overflow-x: auto;
}
.markdown-body :deep(pre code) {
  padding: 0;
  background: transparent;
  font-size: 13px;
}
.markdown-body :deep(code) {
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--wx-code-bg);
  font-family: Consolas, ui-monospace, monospace;
  font-size: 0.88em;
}
.markdown-body :deep(a) {
  color: var(--wx-link);
  text-decoration: none;
}
.markdown-body :deep(a:hover) {
  text-decoration: underline;
}
.markdown-body :deep(blockquote) {
  margin: 10px 0;
  padding: 2px 0 2px 12px;
  border-left: 3px solid var(--color-border);
  color: var(--color-text-secondary);
}
.markdown-body :deep(img) {
  max-width: 100%;
  border-radius: 6px;
}
.markdown-body :deep(table) {
  display: block;
  max-width: 100%;
  margin: 10px 0;
  border-collapse: collapse;
  overflow-x: auto;
  font-size: 14px;
}
.markdown-body :deep(td),
.markdown-body :deep(th) {
  padding: 6px 12px;
  border: 1px solid var(--color-border);
}
.markdown-body :deep(th) {
  background: var(--wx-code-bg);
}
.markdown-body :deep(hr) {
  margin: 14px 0;
  border: 0;
  border-top: 1px solid var(--color-border);
}

/* ---------------- 输入区 ---------------- */
.composer-wrap {
  flex-shrink: 0;
  padding-bottom: env(safe-area-inset-bottom);
  background: var(--color-surface);
}
.ai-disclaimer {
  margin-top: 5px;
  padding: 0 2px;
  color: var(--color-text-secondary);
  font-size: 11px;
  line-height: 1.4;
  opacity: 0.72;
}
.access-hint {
  margin: 8px 0 0;
  text-align: center;
  font-size: 11px;
  color: var(--color-text-secondary);
}
.access-hint {
  margin-bottom: 8px;
}

.sidebar-mask {
  display: none;
}

@media (max-width: 760px) {
  .chat-sidebar {
    position: absolute;
    inset: 0 auto 0 0;
    z-index: 3;
    box-sizing: border-box;
    transform: translateX(-100%);
    transition: transform 0.2s;
  }
  .chat-sidebar.open {
    transform: translateX(0);
  }
  .sidebar-mask {
    display: block;
    position: absolute;
    inset: 0;
    z-index: 2;
    border: 0;
    background: #0006;
  }
  .menu-toggle {
    display: block;
  }
  /* 触摸屏没有 hover，操作按钮常显 */
  .session-actions {
    opacity: 1;
  }
  .chat-header {
    height: 54px;
    padding: 0 16px;
  }
  .chat-body {
    padding: 14px 12px 4px;
  }
  .message-row {
    gap: 8px;
    padding-bottom: 14px;
  }
  .message-avatar {
    width: 36px;
    height: 36px;
    font-size: 15px;
  }
  .bubble {
    max-width: 94%;
    font-size: 14.5px;
    letter-spacing: -0.015em;
    line-height: 1.58;
  }
  .greeting-row .bubble {
    max-width: none;
  }
  .suggestions {
    gap: 8px;
  }
  .suggestions button {
    padding: 12px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .typing i {
    animation: none;
    opacity: 0.55;
  }
  .chat-sidebar,
  .session-actions {
    transition: none;
  }
}
</style>
