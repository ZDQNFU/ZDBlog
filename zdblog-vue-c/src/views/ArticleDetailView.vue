<script setup>
import { ref, watch, nextTick, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import { fetchArticleDetail, likeArticle, unlikeArticle, verifyArticlePassword } from '@/api'
import { extractTOCFromMarkdown, extractTOCFromContainer, slugify } from '@/utils/toc'
import { useAuthStore } from '@/stores/auth'
import { useTheme } from '@/composables/useTheme'
import CommentForm from '@/components/CommentForm.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import AuthModal from '@/components/AuthModal.vue'
import ArticleTOC from '@/components/ArticleTOC.vue'

const route = useRoute()
const auth = useAuthStore()
const { isDark } = useTheme()
const previewTheme = computed(() => isDark.value ? 'vuepress' : 'github')

const article = ref(null)
const loading = ref(false)
const error = ref('')
const showAuthModal = ref(false)
const replyTo = ref(null)
const likeLoading = ref(false)
const toc = ref([])
const contentRef = ref(null)
const commentFormRef = ref(null)

const locked = ref(false)
const password = ref('')
const verifyLoading = ref(false)
const verifyError = ref('')

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function refreshTOC() {
  if (article.value?.content_md) {
    toc.value = extractTOCFromMarkdown(article.value.content_md)
  }
  // 使用 setTimeout 确保 md-editor-v3 完全渲染后再读取 DOM 中的标题
  // md-editor-v3 内部的渲染可能在 Vue nextTick 之后才完成
  setTimeout(() => {
    if (contentRef.value) {
      // 强制给所有标题设置 id，保证与 TOC 中 slugify 生成的 id 一致
      const headings = contentRef.value.querySelectorAll('h1, h2, h3')
      headings.forEach(h => {
        const text = h.textContent.trim()
        if (text) {
          h.id = slugify(text)
        }
      })
      const domToc = extractTOCFromContainer(contentRef.value)
      if (domToc.length) toc.value = domToc
    }
  }, 150)
}

async function loadArticle() {
  try {
    const data = await fetchArticleDetail(route.params.id)
    if (data.locked) {
      locked.value = true
      article.value = data
    } else {
      locked.value = false
      article.value = data
    }
  } catch (e) {
    error.value = e.message || '加载失败'
  }
}

async function handleVerify() {
  if (!password.value || verifyLoading.value) return
  verifyLoading.value = true
  verifyError.value = ''
  try {
    const data = await verifyArticlePassword(route.params.id, password.value)
    locked.value = false
    article.value = data
    nextTick(() => refreshTOC())
  } catch (e) {
    verifyError.value = e.message || '密码错误'
  } finally {
    verifyLoading.value = false
  }
}

watch(article, (val) => {
  if (val) refreshTOC()
})

async function handleCommentPosted() {
  replyTo.value = null
  await loadArticle()
}

function handleReply(comment) {
  replyTo.value = comment
  nextTick(() => {
    commentFormRef.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  })
}

async function handleLike() {
  if (!auth.isAuthenticated) {
    showAuthModal.value = true
    return
  }
  if (likeLoading.value) return
  likeLoading.value = true
  try {
    if (article.value.user_has_liked) {
      const data = await unlikeArticle(article.value.id)
      article.value.like_count = data.like_count
      article.value.user_has_liked = false
    } else {
      const data = await likeArticle(article.value.id)
      article.value.like_count = data.like_count
      article.value.user_has_liked = true
    }
  } catch (e) {
    // 409 conflict = already liked, ignore
  } finally {
    likeLoading.value = false
  }
}

onMounted(async () => {
  loading.value = true
  await loadArticle()
  loading.value = false
})
</script>

<template>
  <div class="article-detail-page">
    <div v-if="loading" class="state-text">加载中...</div>
    <div v-else-if="error" class="state-text error">{{ error }}</div>

    <div v-else-if="article" class="detail-layout">
      <!-- Password prompt for private articles -->
      <div v-if="locked" class="lock-overlay">
        <div class="lock-card">
          <div class="lock-icon">&#128274;</div>
          <h2>这是一篇私密文章</h2>
          <p v-if="article.author_name">需要输入 <strong>{{ article.author_name }}</strong> 的登录密码才能查看</p>
          <el-input
            v-model="password"
            type="password"
            placeholder="请输入作者密码"
            show-password
            :disabled="verifyLoading"
            @keyup.enter="handleVerify"
          />
          <p v-if="verifyError" class="verify-error">{{ verifyError }}</p>
          <el-button type="primary" :loading="verifyLoading" @click="handleVerify" style="width:100%">
            验证
          </el-button>
        </div>
        <div class="article-preview">
          <header class="article-header">
            <h1 class="article-title">{{ article.title }} <span class="private-badge-detail">私密</span></h1>
            <div class="article-meta">
              <span v-if="article.author_name" class="meta-author">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                {{ article.author_name }}
              </span>
              <span class="meta-time" v-if="article.published_at">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
                发布于 {{ formatDate(article.published_at) }}
              </span>
            </div>
            <div class="article-stats">
              <span><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z"/></svg> {{ article.like_count ?? 0 }} 次赞</span>
              <span><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg> {{ article.comment_count ?? 0 }} 条评论</span>
              <span><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg> {{ article.view_count ?? 0 }} 次浏览</span>
            </div>
          </header>
        </div>
      </div>

      <ArticleTOC v-if="!locked" :toc="toc" />

      <article v-if="!locked" class="article-body">
        <header class="article-header">
          <h1 class="article-title">{{ article.title }}</h1>

          <div class="article-meta">
            <span v-if="article.author_name" class="meta-author">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              {{ article.author_name }}
            </span>

            <span class="meta-time">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
              发布于 {{ formatDate(article.published_at) }}
            </span>

            <span class="meta-time" v-if="article.updated_at !== article.published_at">
              更新于 {{ formatDate(article.updated_at) }}
            </span>
          </div>

          <div class="article-tags-cat" v-if="article.category || article.tags?.length">
            <span class="category" v-if="article.category">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
              {{ article.category.name }}
            </span>
            <span
              class="tag"
              v-for="tag in article.tags"
              :key="tag.id"
              :style="{ background: tag.color + '22', color: tag.color }"
            >
              {{ tag.name }}
            </span>
          </div>

          <div class="article-stats">
            <button
              class="like-btn"
              :class="{ liked: article.user_has_liked }"
              :disabled="likeLoading"
              @click="handleLike"
              :title="article.user_has_liked ? '取消点赞' : '点赞'"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" :fill="article.user_has_liked ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z"/></svg>
              {{ article.like_count ?? 0 }} 次赞
            </button>
            <span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              {{ article.comment_count ?? 0 }} 条评论
            </span>
            <span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
              {{ article.view_count ?? 0 }} 次浏览
            </span>
          </div>
        </header>

        <div ref="contentRef" class="article-content">
          <MdPreview class="md"
            v-if="article.content_md"
            :modelValue="article.content_md"
            :theme="isDark ? 'dark' : 'light'"
            :previewTheme="previewTheme"
          />
          <div v-else v-html="article.content_html"></div>
        </div>

        <div ref="commentFormRef">
          <CommentForm
            :article-id="article.id"
            :reply-to="replyTo"
            @posted="handleCommentPosted"
            @login-request="showAuthModal = true"
            @cancel-reply="replyTo = null"
          />
        </div>

        <section class="comments-section" v-if="article.comments?.length">
          <h3>评论 ({{ article.comment_count }})</h3>
          <div class="comment" v-for="c in article.comments" :key="c.id">
            <div class="comment-header">
              <UserAvatar :name="c.author_name" />
              <span class="comment-author">{{ c.author_name }}</span>
              <span class="comment-time">{{ formatDate(c.created_at) }}</span>
            </div>
            <p class="comment-body">{{ c.content }}</p>
            <button class="reply-btn" @click="handleReply(c)">回复</button>

            <div class="replies" v-if="c.replies?.length">
              <div class="comment reply" v-for="r in c.replies" :key="r.id">
                <div class="comment-header">
                  <UserAvatar :name="r.author_name" />
                  <span class="comment-author">{{ r.author_name }}</span>
                  <span class="comment-time">{{ formatDate(r.created_at) }}</span>
                </div>
                <p class="comment-body">{{ r.content }}</p>
                <button class="reply-btn" @click="handleReply(c)">回复</button>
              </div>
            </div>
          </div>
        </section>
      </article>
    </div>

    <AuthModal v-if="showAuthModal" @close="showAuthModal = false" @logged-in="loadArticle" />
  </div>
</template>

<style scoped>
.article-detail-page {
  padding-top: calc(var(--navbar-height) + 32px);
  padding-bottom: 48px;
}

.state-text {
  text-align: center;
  color: var(--color-text-secondary);
  padding: 48px 0;
}
.error { color: #ef4444; }

/* ---- Lock overlay (private article) ---- */
.lock-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 32px;
  padding: 48px 24px 0;
  width: 100%;
}
.lock-card {
  background: var(--color-surface);
  border-radius: 16px;
  padding: 40px 36px;
  max-width: 420px;
  width: 100%;
  text-align: center;
  box-shadow: 0 4px 24px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.lock-icon {
  font-size: 3rem;
  margin-bottom: 4px;
}
.lock-card h2 {
  font-size: 1.2rem;
  font-weight: 600;
  margin: 0;
}
.lock-card p {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  margin: 0;
}
.verify-error {
  color: #ef4444;
  font-size: 0.85rem;
  margin: 0;
}
.article-preview {
  max-width: 700px;
  width: 100%;
  opacity: 0.5;
  pointer-events: none;
}
.private-badge-detail {
  display: inline-block;
  vertical-align: middle;
  padding: 2px 10px;
  border-radius: 10px;
  background: #fef3c7;
  color: #d97706;
  font-size: 0.75rem;
  font-weight: 500;
  margin-left: 8px;
}

.detail-layout {
  display: flex;
  justify-content: center;
  gap: 40px;
  padding: 0 24px;
}

.article-body {
  max-width: 1080px;
  width: 100%;
  padding: 0 40px;
  border-left: 1px solid var(--color-border);
  border-right: 1px solid var(--color-border);
}


@media (max-width: 1024px) {
  .detail-layout {
    justify-content: flex-start;
    gap: 0;
    padding: 0 16px;
  }
  .article-body {
    max-width: 100%;
    padding: 0 16px;
    border-left: none;
    border-right: none;
  }
}

.article-header {
  margin-bottom: 32px;
}

.article-title {
  font-size: 1.8rem;
  font-weight: 700;
  line-height: 1.35;
  margin-bottom: 14px;
}

.article-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin-bottom: 14px;
}

.meta-author,
.meta-time {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.article-tags-cat {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.category {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 12px;
  border-radius: 12px;
  background: var(--color-bg);
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.tag {
  display: inline-block;
  padding: 3px 12px;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
}

.article-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}
.article-stats span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.like-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: none;
  border: none;
  font-size: inherit;
  color: inherit;
  cursor: pointer;
  padding: 4px 10px;
  border-radius: 6px;
  transition: color 0.2s, background 0.2s;
}
.like-btn:hover {
  color: var(--color-primary);
  background: rgba(59, 130, 246, 0.06);
}
.like-btn.liked {
  color: var(--color-primary);
}
.like-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

/* article content rendered by md-editor-v3 */
.article-content {
  font-size: 1rem;
  line-height: 1.85;
  margin-bottom: 48px;
}

.md {
  /* padding: 5px; */
  border-radius: 15px;
  background: var(--color-bg);
}

/* 覆盖 md-editor-v3 内部预览区域的默认背景 */
.article-content :deep(.md-editor-preview-wrapper) {
  background: var(--color-bg) !important;
}
.article-content :deep(.md-editor-preview) {
  background: var(--color-bg) !important;
}

/* 修复 md-editor-v3 代码块头部（"javascript 复制代码"）z-index 过高，
   滚动时盖在导航栏上方的问题 */
.article-content :deep(.md-editor-code) {
  position: relative;
  z-index: 0;
}
.article-content :deep(.md-editor-code-head) {
  z-index: 0 !important;
}

.article-content :deep(h1),
.article-content :deep(h2),
.article-content :deep(h3),
.article-content :deep(h4) {
  margin: 1.5em 0 0.5em;
  scroll-margin-top: calc(var(--navbar-height) + 16px);
}

.article-content :deep(p) {
  margin: 0.75em 0;
}
.article-content :deep(img) {
  max-width: 100%;
  border-radius: 6px;
}

.article-content :deep(blockquote) {
  border-left: 3px solid var(--color-primary);
  margin: 1em 0;
  padding: 0.5em 1em;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  border-radius: 0 6px 6px 0;
}
.article-content :deep(a) {
  color: var(--color-primary);
}
.article-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1em 0;
}
.article-content :deep(th),
.article-content :deep(td) {
  border: 1px solid var(--color-border);
  padding: 8px 12px;
  text-align: left;
}
.article-content :deep(th) {
  background: var(--color-bg);
  font-weight: 600;
}
.article-content :deep(ul),
.article-content :deep(ol) {
  padding-left: 1.5em;
  margin: 0.5em 0;
}
.article-content :deep(li) {
  margin: 0.25em 0;
}
.article-content :deep(hr) {
  border: none;
  border-top: 1px solid var(--color-border);
  margin: 2em 0;
}

/* comments */
.comments-section {
  border-top: 1px solid var(--color-border);
  padding-top: 32px;
}
.comments-section h3 {
  font-size: 1.1rem;
  margin-bottom: 20px;
}

.comment {
  padding: 14px 0;
  border-bottom: 1px solid var(--color-border);
}
.comment.reply {
  margin-left: 28px;
  border-bottom: none;
  border-top: 1px solid var(--color-border);
  margin-top: 8px;
}
.comment-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 2px;
}
.comment-author {
  font-weight: 600;
  font-size: 0.9rem;
}
.comment-time {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}
.comment-body {
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--color-text);
  margin-bottom: 6px;
}
.reply-btn {
  background: none;
  border: none;
  color: var(--color-text-secondary);
  font-size: 0.78rem;
  cursor: pointer;
  padding: 2px 8px;
  border-radius: 4px;
  transition: color 0.2s, background 0.2s;
}
.reply-btn:hover {
  color: var(--color-primary);
  background: rgba(59, 130, 246, 0.06);
}
</style>
