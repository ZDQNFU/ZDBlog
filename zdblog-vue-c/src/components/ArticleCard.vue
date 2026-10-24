<script setup>
defineProps({
  article: { type: Object, required: true },
  reverseCut: { type: Boolean, default: false },
})

function formatDate(value) {
  if (!value) return ''
  return new Date(value).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}
</script>

<template>
  <router-link :to="`/article/${article.id}`" class="article-card" :class="{ 'cut-reverse': reverseCut }">
    <div class="card-cover">
      <img v-if="article.cover" :src="article.cover" :alt="article.title" loading="lazy" decoding="async" />
      <div v-else class="cover-placeholder" aria-hidden="true">
        <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.1"><path d="M12 7C9 4 5 4 2 5v14c3-1 7-1 10 2 3-3 7-3 10-2V5c-3-1-7-1-10 2Z"/><path d="M12 7v14"/></svg>
      </div>
      <div class="cover-shade"></div>
      <div class="cover-info">
        <span class="cover-category">{{ article.category?.name || '文字记录' }}</span>
        <time v-if="article.published_at" :datetime="article.published_at">{{ formatDate(article.published_at) }}</time>
      </div>
    </div>
    <div class="card-body">
      <h2 class="card-title">{{ article.title }}<span v-if="article.status === 'private'" class="private-badge">私密</span></h2>
      <p v-if="article.summary" class="card-summary">{{ article.summary }}</p>
      <div v-if="article.tags?.length" class="card-tags">
        <span v-for="tag in article.tags" :key="tag.id" class="tag" :style="{ '--tag-color': tag.color || 'var(--color-primary)' }"># {{ tag.name }}</span>
      </div>
      <div class="card-bottom">
        <div class="card-meta">
          <span v-if="article.author_name" class="meta-author">{{ article.author_name }}</span>
          <span class="meta-item" :aria-label="`${article.like_count ?? 0} 次赞`">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9A2 2 0 0 0 19.68 9H14Z"/></svg>{{ article.like_count ?? 0 }}
          </span>
          <span class="meta-item" :aria-label="`${article.comment_count ?? 0} 条评论`">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z"/></svg>{{ article.comment_count ?? 0 }}
          </span>
        </div>
        <span class="card-read">阅读全文 <span aria-hidden="true">↗</span></span>
      </div>
    </div>
  </router-link>
</template>

<style scoped>
.article-card {
  --cut: 48px;
  display: grid;
  grid-template-columns: 37% minmax(0, 1fr);
  min-height: 256px;
  border: 1px solid var(--color-border);
  border-radius: 18px;
  overflow: hidden;
  background: var(--floating-surface);
  box-shadow: 0 8px 32px #102d4424;
  transition: box-shadow .25s, transform .25s;
}
.article-card:hover { transform: translateY(-3px); box-shadow: 0 14px 40px #102d4438; }
.card-cover { position: relative; width: calc(100% + var(--cut)); min-width: 0; overflow: hidden; clip-path: polygon(0 0, 100% 0, calc(100% - var(--cut)) 100%, 0 100%); }
.cut-reverse .card-cover { clip-path: polygon(0 0, calc(100% - var(--cut)) 0, 100% 100%, 0 100%); }
.card-cover::after { content: ''; position: absolute; inset: 0; background: #ffffffa0; clip-path: polygon(calc(100% - 2px) 0, 100% 0, calc(100% - var(--cut)) 100%, calc(100% - var(--cut) - 2px) 100%); }
.cut-reverse .card-cover::after { clip-path: polygon(calc(100% - var(--cut) - 2px) 0, calc(100% - var(--cut)) 0, 100% 100%, calc(100% - 2px) 100%); }
.card-cover img, .cover-placeholder, .cover-shade { position: absolute; inset: 0; width: 100%; height: 100%; }
.card-cover img { object-fit: cover; transition: transform .6s; }
.article-card:hover .card-cover img { transform: scale(1.045); }
.cover-placeholder { display: grid; place-items: center; background: color-mix(in srgb, var(--color-primary) 28%, var(--color-bg)); color: var(--color-primary); }
.cover-shade { background: linear-gradient(0deg, #102b43c9, #102b4300 68%); }
.cover-info { position: absolute; bottom: 24px; left: 24px; right: calc(var(--cut) + 12px); display: flex; align-items: flex-start; flex-direction: column; gap: 9px; color: white; text-shadow: 0 1px 8px #102b4380; }
.cover-category { font-size: .83rem; letter-spacing: .06em; font-weight: 600; }
.cover-info time { font-size: .7rem; opacity: .85; font-variant-numeric: tabular-nums; }
.card-body { min-width: 0; padding: 28px 30px 24px calc(var(--cut) + 22px); display: flex; flex-direction: column; justify-content: center; }
.card-title { font-size: 1.32rem; line-height: 1.55; font-weight: 650; overflow-wrap: anywhere; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; transition: color .2s; }
.article-card:hover .card-title { color: var(--color-primary); }
.private-badge { vertical-align: middle; margin-left: 8px; font-size: .66rem; padding: 2px 8px; border-radius: 5px; color: #946114; background: #fef3c7; }
.card-summary { font-size: .88rem; line-height: 1.85; color: var(--color-text-secondary); margin-top: 12px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; overflow-wrap: anywhere; }
.card-tags { display: flex; flex-wrap: wrap; gap: 6px 14px; margin-top: 14px; }
.tag { font-size: .73rem; color: var(--tag-color); }
.card-bottom { margin-top: auto; padding-top: 20px; display: flex; gap: 16px; justify-content: space-between; align-items: center; }
.card-meta { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; color: var(--color-text-secondary); font-size: .72rem; }
.meta-item { display: inline-flex; align-items: center; gap: 4px; }
.meta-author { max-width: 90px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.card-read { display: flex; gap: 14px; align-items: center; font-size: .75rem; color: var(--color-primary); white-space: nowrap; }
@media (max-width: 767px) {
  .article-card { --cut: 28px; grid-template-columns: 32% minmax(0, 1fr); min-height: 210px; border-radius: 14px; }
  .card-body { padding: 20px 18px 18px calc(var(--cut) + 12px); }
  .card-title { font-size: 1.05rem; }
  .card-summary { font-size: .79rem; line-height: 1.7; margin-top: 8px; }
  .card-tags { margin-top: 10px; gap: 5px 10px; }
  .card-bottom { padding-top: 14px; gap: 8px; }
  .meta-author { display: none; }
  .card-meta { gap: 8px; }
  .card-read { font-size: .7rem; gap: 6px; }
  .cover-info { left: 14px; bottom: 20px; right: calc(var(--cut) + 6px); }
  .cover-category { font-size: .72rem; }
  .cover-info time { font-size: .6rem; }
}
@media (max-width: 400px) {
  .article-card { --cut: 20px; grid-template-columns: 29% minmax(0, 1fr); }
  .card-body { padding-right: 12px; padding-left: calc(var(--cut) + 10px); }
  .card-title { font-size: .95rem; }
  .card-read { font-size: .66rem; gap: 4px; }
  .cover-info { left: 10px; }
}
</style>
