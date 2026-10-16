<script setup>
defineProps({
  article: {
    type: Object,
    required: true,
  },
})

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}
</script>

<template>
  <router-link :to="`/article/${article.id}`" class="card">
    <div class="card-cover" v-if="article.cover">
      <img :src="article.cover" :alt="article.title" />
    </div>
    <div class="card-body">
      <h2 class="card-title">
        {{ article.title }}
        <span v-if="article.status === 'private'" class="private-badge">私密</span>
      </h2>
      <p class="card-summary" v-if="article.summary">{{ article.summary }}</p>

      <div class="card-tags" v-if="article.tags?.length">
        <span
          class="tag"
          v-for="tag in article.tags"
          :key="tag.id"
          :style="{ background: tag.color + '22', color: tag.color }"
        >
          {{ tag.name }}
        </span>
      </div>

      <div class="card-meta">
        <span class="meta-item" v-if="article.category">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
          {{ article.category.name }}
        </span>
        <span class="meta-item">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z"/></svg>
          {{ article.like_count ?? 0 }}
        </span>
        <span class="meta-item">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          {{ article.comment_count ?? 0 }}
        </span>
        <span class="meta-item">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
          {{ formatDate(article.published_at) }}
        </span>
        <span class="meta-author" v-if="article.author_name">
          {{ article.author_name }}
        </span>
      </div>
    </div>
  </router-link>
</template>

<style scoped>
.card {
  display: block;
  background: var(--color-surface);
  border-radius: var(--radius);
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: var(--shadow-card);
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-card-hover);
}

.card-cover {
  position: relative;
}
.card-cover::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 40%;
  /* 设置顶部到底部的渐变过渡 */
  background: linear-gradient(to bottom, transparent 80%, var(--color-surface) 100%);
  pointer-events: none;
}
.card-cover img {
  display: block;
  width: 100%;
  height: 180px;
  object-fit: cover;
}

.card-body {
  padding: 20px;
}

.card-title {
  font-size: 1.15rem;
  font-weight: 600;
  line-height: 1.4;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-summary {
  color: var(--color-text-secondary);
  font-size: 0.9rem;
  line-height: 1.55;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.meta-author {
  margin-left: auto;
  font-weight: 500;
  color: var(--color-text);
}

.private-badge {
  display: inline-block;
  vertical-align: middle;
  padding: 2px 10px;
  border-radius: 10px;
  background: #fef3c7;
  color: #d97706;
  font-size: 0.7rem;
  font-weight: 500;
  margin-left: 8px;
}
</style>
