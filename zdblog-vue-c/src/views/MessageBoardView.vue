<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { fetchMessages, createMessage, likeMessage, unlikeMessage } from '@/api'
import { useTheme } from '@/composables/useTheme'
import AuthModal from '@/components/AuthModal.vue'
import EmojiPicker from '@/components/EmojiPicker.vue'
import MessageCard from '@/components/MessageCard.vue'
import '@/assets/messageComposer.css'

const auth = useAuthStore()
const { isDark } = useTheme()

const messages = ref([])
const cards = ref([])
const content = ref('')
const showEmoji = ref(false)
const showAuthModal = ref(false)
const submitting = ref(false)
const feedback = ref('')
const feedbackError = ref(false)
const speedMultiplier = ref(1)

const TRACKS = 9
const BASE_DURATION = 10

const lightColors = ['#e74c3c','#e67e22','#2ecc71','#1abc9c','#3498db','#9b59b6','#e91e63','#00bcd4','#ff5722','#673ab7','#009688','#f44336','#3f51b5','#4caf50','#795548']
const darkColors = ['#ff6b6b','#ffd93d','#6bcb77','#4dd9c1','#60a5fa','#c084fc','#f472b6','#38bdf8','#fb923c','#a78bfa','#2dd4bf','#fbbf24','#818cf8','#34d399','#f87171']

let pollTimer = null
let launchTimer = null
let uid = 0
const occupiedTracks = new Set()

function randomColor() {
  const p = isDark.value ? darkColors : lightColors
  return p[Math.floor(Math.random() * p.length)]
}

function pickTrack() {
  const free = []
  for (let i = 0; i < TRACKS; i++) {
    if (!occupiedTracks.has(i)) free.push(i)
  }
  if (free.length === 0) return -1
  return free[Math.floor(Math.random() * free.length)]
}

function addCard(msg) {
  const track = pickTrack()
  if (track === -1) return
  occupiedTracks.add(track)
  const color = msg._color || randomColor()
  msg._color = color
  cards.value.push({
    id: ++uid,
    message: msg,
    color,
    track,
    duration: BASE_DURATION / speedMultiplier.value,
  })
}

function removeCard(id) {
  const card = cards.value.find(c => c.id === id)
  if (card) occupiedTracks.delete(card.track)
  cards.value = cards.value.filter(c => c.id !== id)
}

async function handleLike(msg) {
  if (!auth.isAuthenticated) {
    showAuthModal.value = true
    return
  }
  try {
    if (msg.user_has_liked) {
      await unlikeMessage(msg.id)
      msg.user_has_liked = false
    } else {
      await likeMessage(msg.id)
      msg.user_has_liked = true
    }
  } catch {}
}

async function loadMessages() {
  try {
    const data = await fetchMessages()
    messages.value = Array.isArray(data) ? data : (data.results || [])
    const visibleIds = new Set(messages.value.map(message => message.id))
    for (const card of [...cards.value]) {
      if (!visibleIds.has(card.message.id)) removeCard(card.id)
    }
  } catch {}
}

function randomLaunch() {
  if (!messages.value.length) return
  addCard(messages.value[Math.floor(Math.random() * messages.value.length)])
}

async function handleSend() {
  if (!content.value.trim() || submitting.value) return
  submitting.value = true
  feedback.value = ''
  feedbackError.value = false
  try {
    const result = await createMessage(content.value.trim())
    feedback.value = result.message || '留言发送成功'
    if (result.status === 'rejected') {
      feedbackError.value = true
      return
    }
    content.value = ''
    showEmoji.value = false
    await loadMessages()
  } catch (error) {
    feedback.value = error.message || '留言发送失败，请稍后重试'
    feedbackError.value = true
  } finally { submitting.value = false }
}

function insertEmoji(emoji) {
  content.value += emoji
  showEmoji.value = false
}

onMounted(async () => {
  await nextTick()
  await loadMessages()
  launchTimer = setInterval(randomLaunch, 700)
  pollTimer = setInterval(loadMessages, 5000)
})

onUnmounted(() => {
  clearInterval(pollTimer)
  clearInterval(launchTimer)
})
</script>

<template>
  <div class="dm-page">
    <div class="dm-stage">
      <MessageCard
        v-for="card in cards"
        :key="card.id"
        :message="card.message"
        :color="card.color"
        :track="card.track"
        :duration="card.duration"
        @done="removeCard(card.id)"
        @like="handleLike"
      />
    </div>

    <p v-if="feedback" class="dm-feedback" :class="{ error: feedbackError }" :role="feedbackError ? 'alert' : 'status'">{{ feedback }}</p>
    <div class="dm-input-bar">
      <button class="dm-emoji-btn" :disabled="submitting" @click="showEmoji = !showEmoji">😀</button>
      <input
        v-model="content"
        class="dm-msg-input"
        maxlength="100"
        :disabled="submitting"
        placeholder="发送友善留言，内容将自动审核..."
        @input="feedback = ''"
        @keydown.enter="handleSend"
      />
      <button class="dm-send-btn" :disabled="!content.trim() || submitting" @click="handleSend">发送</button>
      <div class="dm-speed">
        <span>速度</span>
        <input type="range" min="0.5" max="3" step="0.1" v-model="speedMultiplier" />
      </div>
    </div>

    <EmojiPicker :visible="showEmoji" @select="insertEmoji" @close="showEmoji = false" />
    <AuthModal v-if="showAuthModal" @close="showAuthModal = false" />
  </div>
</template>

<style scoped>
.dm-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-bg);
  box-sizing: border-box;
  padding-top: var(--navbar-height);
}

.dm-stage {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.dm-feedback {
  margin: 0;
  padding: 10px 16px;
  flex-shrink: 0;
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text-secondary);
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
}
.dm-feedback.error { color: #ef4444; }

/* ---- input bar ---- */

.dm-speed {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; color: var(--color-text-secondary);
}
.dm-speed input { width: 80px; accent-color: var(--color-primary); }

@media (max-width: 768px) {
  .dm-speed { display: none; }
}
</style>
