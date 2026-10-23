<script setup>
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { createComment } from '@/api'
import EmojiPicker from '@/components/EmojiPicker.vue'

const props = defineProps({
  articleId: { type: String, required: true },
  replyTo: { type: Object, default: null },
})

const emit = defineEmits(['posted', 'login-request', 'cancel-reply'])

const auth = useAuthStore()
const content = ref('')
const submitting = ref(false)
const error = ref('')
const notice = ref('')
const noticeStatus = ref('')
const showEmoji = ref(false)
const textareaRef = ref(null)

async function handleSubmit() {
  if (submitting.value || !content.value.trim()) return
  submitting.value = true
  error.value = ''
  notice.value = ''
  try {
    const parentId = props.replyTo?.id || null
    const result = await createComment(props.articleId, content.value.trim(), parentId)
    if (result.status === 'rejected') {
      error.value = result.message
      return
    }
    content.value = ''
    notice.value = result.message || '评论发表成功'
    noticeStatus.value = result.status
    emit('posted', result)
  } catch (e) {
    error.value = e.message
  } finally {
    submitting.value = false
  }
}

function insertEmoji(emoji) {
  const el = textareaRef.value
  if (el) {
    const start = el.selectionStart
    const end = el.selectionEnd
    content.value = content.value.slice(0, start) + emoji + content.value.slice(end)
    // Restore cursor after the inserted emoji
    setTimeout(() => {
      el.selectionStart = el.selectionEnd = start + emoji.length
      el.focus()
    }, 0)
  } else {
    content.value += emoji
  }
  showEmoji.value = false
}
</script>

<template>
  <div class="comment-form">
    <div v-if="!auth.isAuthenticated" class="login-hint">
      <span>请先登录后发表评论</span>
      <button class="login-trigger-btn" @click="emit('login-request')">登录 / 注册</button>
    </div>

    <template v-else>
      <div v-if="replyTo" class="reply-hint">
        回复 <strong>{{ replyTo.author_name }}</strong>
        <button class="cancel-reply-btn" @click="emit('cancel-reply')">取消回复</button>
      </div>
      <div v-if="error" class="form-error" role="alert">{{ error }}</div>
      <div v-if="notice" class="form-notice" :class="{ pending: noticeStatus === 'pending' }" role="status">{{ notice }}</div>
      <div class="textarea-wrapper">
        <textarea
          ref="textareaRef"
          v-model="content"
          class="comment-textarea"
          :placeholder="replyTo ? '写下你的回复...' : '写下你的评论...'"
          rows="3"
          maxlength="2000"
          :disabled="submitting"
          @input="error = ''; notice = ''"
        ></textarea>
        <button class="emoji-toggle-btn" @click="showEmoji = !showEmoji" title="表情">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
            <line x1="9" y1="9" x2="9.01" y2="9"/>
            <line x1="15" y1="9" x2="15.01" y2="9"/>
          </svg>
        </button>
      </div>
      <EmojiPicker :visible="showEmoji" @select="insertEmoji" @close="showEmoji = false" />
      <div class="form-actions">
        <span class="form-note">以 <strong>{{ auth.user?.username }}</strong> 的身份发表 · {{ content.length }}/2000<br />评论将自动审核，请文明交流</span>
        <button class="submit-btn" :disabled="submitting || !content.trim()" @click="handleSubmit">
          {{ submitting ? '提交中...' : '发表评论' }}
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.comment-form {
  margin-bottom: 28px;
  padding: 16px;
  background: var(--color-bg);
  border-radius: 10px;
}

.login-hint {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--color-text-secondary);
  font-size: 0.9rem;
}

.login-trigger-btn {
  padding: 6px 18px;
  border: 1px solid var(--color-primary);
  border-radius: 8px;
  background: transparent;
  color: var(--color-primary);
  font-size: 0.85rem;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}
.login-trigger-btn:hover {
  background: var(--color-primary);
  color: #fff;
}

.reply-hint {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}
.reply-hint strong {
  color: var(--color-primary);
}
.cancel-reply-btn {
  background: none;
  border: none;
  color: var(--color-text-secondary);
  font-size: 0.8rem;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  transition: color 0.2s, background 0.2s;
}
.cancel-reply-btn:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.06);
}

.form-error {
  background: #fef2f2;
  color: #dc2626;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 0.85rem;
  margin-bottom: 8px;
}

.form-notice {
  color: var(--color-primary);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 0.85rem;
  margin-bottom: 8px;
}
.form-notice.pending { color: var(--color-text-secondary); }

.textarea-wrapper {
  position: relative;
}

.comment-textarea {
  width: 100%;
  padding: 12px 40px 12px 12px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  font-size: 0.9rem;
  font-family: inherit;
  line-height: 1.6;
  resize: vertical;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  background: var(--color-surface);
  color: var(--color-text);
}

.emoji-toggle-btn {
  position: absolute;
  right: 6px;
  bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.emoji-toggle-btn:hover {
  background: var(--color-bg);
  color: var(--color-primary);
}
.comment-textarea:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.form-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
}

.form-note {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.submit-btn {
  padding: 8px 22px;
  border: none;
  border-radius: 8px;
  background: var(--color-primary);
  color: #fff;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.15s;
}
.submit-btn:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}
.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
