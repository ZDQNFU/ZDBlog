<script setup>
import { ref, onMounted } from 'vue'
import { fetchMoments, likeMoment, unlikeMoment } from '@/api'
import UserAvatar from '@/components/UserAvatar.vue'
import Pagination from '@/components/Pagination.vue'

const moments = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(true)
const error = ref('')
const feedback = ref('')
const likingIds = ref(new Set())
let loadId = 0

function formatDate(value) {
  return new Date(value).toLocaleString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
function wasEdited(moment) {
  return new Date(moment.updated_at) - new Date(moment.created_at) > 1000
}

async function load(nextPage = 1) {
  const id = ++loadId
  loading.value = true
  error.value = ''
  feedback.value = ''
  try {
    const data = await fetchMoments(nextPage, pageSize)
    if (id !== loadId) return
    moments.value = data.results
    total.value = data.count
    page.value = nextPage
  } catch (e) {
    if (id !== loadId) return
    if (e.status === 404 && nextPage > 1) await load(1)
    else error.value = e.message || '动态加载失败，请稍后再试'
  } finally {
    if (id === loadId) loading.value = false
  }
}

async function toggleLike(moment) {
  if (likingIds.value.has(moment.id)) return
  likingIds.value.add(moment.id)
  feedback.value = ''
  try {
    const data = moment.user_has_liked ? await unlikeMoment(moment.id) : await likeMoment(moment.id)
    moment.like_count = data.like_count
    moment.user_has_liked = data.liked
  } catch (e) {
    if (e.status === 404) {
      await load(page.value)
      feedback.value = '这条动态已下线，列表已刷新'
    } else feedback.value = e.message || '点赞失败，请稍后重试'
  } finally {
    likingIds.value.delete(moment.id)
  }
}

function changePage(nextPage) {
  load(nextPage)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
onMounted(() => load())
</script>

<template>
  <main class="moments-page">
    <header class="moments-heading">
      <div><p class="section-eyebrow">记录当下</p><h1>动态<span v-if="total" class="article-count">{{ total }} 条记录</span></h1><p class="heading-description">一些片段，一点近况。</p></div>
      <span class="heading-symbol" aria-hidden="true">“</span>
    </header>

    <p v-if="loading" class="state-panel" role="status">正在翻阅近况…</p>
    <div v-else-if="error" class="state-panel error" role="alert"><p>{{ error }}</p><button class="retry-button" @click="load(page)">重新加载</button></div>
    <section v-else-if="!moments.length" class="state-panel empty-state"><h2>暂时还没有动态</h2><p>下一次分享，或许就在不久之后。</p></section>
    <ol v-else class="moment-list" aria-label="站主动态">
      <li v-for="moment in moments" :key="moment.id" class="moment-item">
        <article class="moment-card">
          <header class="moment-header">
            <UserAvatar :name="moment.author_name || '站主'" :size="38" />
            <div class="moment-author"><div><span class="author-name">{{ moment.author_name || '站主' }}</span><span class="owner-badge">站主</span></div><time :datetime="moment.created_at">{{ formatDate(moment.created_at) }}</time></div>
          </header>
          <p class="moment-content">{{ moment.content }}</p>
          <footer class="moment-footer">
            <button class="like-button" :class="{ liked: moment.user_has_liked }" :disabled="likingIds.has(moment.id)" :aria-pressed="moment.user_has_liked" :aria-label="`${moment.user_has_liked ? '取消点赞' : '点赞'}，${moment.like_count} 次赞`" @click="toggleLike(moment)">
              <svg width="18" height="18" viewBox="0 0 24 24" :fill="moment.user_has_liked ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"/></svg>
              <span>{{ moment.user_has_liked ? '已赞' : '赞' }}</span><span class="like-count">{{ moment.like_count }}</span>
            </button>
            <span v-if="wasEdited(moment)" class="edited-at" :title="`更新于 ${formatDate(moment.updated_at)}`">已编辑</span>
          </footer>
        </article>
      </li>
    </ol>
    <p v-if="feedback" class="feedback" role="alert">{{ feedback }}</p>
    <Pagination v-if="!loading && !error" :current="page" :total="total" :page-size="pageSize" @change="changePage" />
  </main>
</template>

<style scoped>
.moments-page { width: 100%; max-width: 900px; margin: 0 auto; padding: calc(var(--navbar-height) + 36px) 24px 64px; }
.moments-heading { display: flex; align-items: center; justify-content: space-between; gap: 24px; padding: 28px 32px; margin-bottom: 28px; border: 1px solid var(--color-border); border-radius: var(--radius); background: var(--floating-surface); box-shadow: var(--shadow-card); }
.moments-heading h1 { font-size: 1.85rem; line-height: 1.5; }
.heading-description { margin-top: 7px; font-size: .85rem; color: var(--color-text-secondary); }
.heading-symbol { color: var(--color-primary); opacity: .2; font: 100px/1 Georgia, serif; height: 65px; }
.moment-list { position: relative; list-style: none; padding-left: 26px; }
.moment-list::before { content: ''; position: absolute; left: 4px; top: 32px; bottom: 32px; width: 1px; background: color-mix(in srgb, var(--color-primary) 40%, transparent); }
.moment-item { position: relative; margin-bottom: 22px; }
.moment-item::before { content: ''; position: absolute; left: -25px; top: 31px; width: 7px; height: 7px; border-radius: 50%; background: var(--color-primary); box-shadow: 0 0 0 4px var(--floating-surface); }
.moment-card { padding: 26px 30px 18px; border: 1px solid var(--color-border); border-radius: 16px; background: var(--floating-surface); box-shadow: var(--shadow-card); }
.moment-header { display: flex; align-items: center; gap: 12px; }
.author-name { font-size: .9rem; font-weight: 650; }
.owner-badge { margin-left: 9px; padding: 2px 7px; border-radius: 4px; color: var(--color-primary); background: color-mix(in srgb, var(--color-primary) 9%, transparent); font-size: .64rem; }
.moment-author time { display: block; margin-top: 2px; font-size: .72rem; color: var(--color-text-secondary); }
.moment-content { margin: 22px 0 24px; white-space: pre-wrap; overflow-wrap: anywhere; font-size: 1rem; line-height: 1.95; }
.moment-footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding-top: 12px; border-top: 1px solid var(--color-border); }
.like-button { display: inline-flex; align-items: center; gap: 7px; padding: 6px 9px; margin-left: -9px; background: transparent; border: none; border-radius: 8px; color: var(--color-text-secondary); font: inherit; font-size: .78rem; cursor: pointer; transition: background .2s, color .2s; }
.like-button:hover, .like-button.liked { color: #e16b7d; background: color-mix(in srgb, #e16b7d 8%, transparent); }
.like-button:disabled { opacity: .5; cursor: wait; }
.like-count { font-variant-numeric: tabular-nums; }
.edited-at { color: var(--color-text-secondary); font-size: .68rem; }
.state-panel { padding: 48px 24px; text-align: center; border-radius: 16px; background: var(--floating-surface); color: var(--color-text-secondary); }
.empty-state h2 { color: var(--color-text); font-size: 1.1rem; margin-bottom: 10px; }
.empty-state p { font-size: .85rem; }
.error, .feedback { color: #d85d70; }
.feedback { background: var(--floating-surface); padding: 12px 18px; border-radius: 10px; font-size: .85rem; }
.retry-button { margin-top: 14px; border: none; background: none; color: var(--color-primary); font: inherit; cursor: pointer; }
@media (max-width: 600px) {
  .moments-page { padding: calc(var(--navbar-height) + 22px) 16px 36px; }
  .moments-heading { padding: 22px; margin-bottom: 24px; }
  .moments-heading h1 { font-size: 1.55rem; }
  .moment-list { padding-left: 18px; }
  .moment-item::before { left: -17px; }
  .moment-card { padding: 22px 20px 14px; }
  .moment-content { font-size: .94rem; margin: 18px 0 20px; }
}
</style>
