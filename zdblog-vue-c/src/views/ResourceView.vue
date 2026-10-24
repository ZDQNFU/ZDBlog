<script setup>
import { ref, onMounted } from 'vue'
import { fetchLinks } from '@/api'

const links = ref([])
const loading = ref(false)
const error = ref('')

function avatarLetter(name) {
  return name?.charAt(0)?.toUpperCase() || '?'
}

onMounted(async () => {
  loading.value = true

  try {
    const data = await fetchLinks()
    links.value = data.results || data || []
  } catch (e) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="resource-page">
    <div class="page-header">
      <p class="section-eyebrow">我的互联网收藏夹</p>
      <h1>资源分享</h1>
      <p>收藏的一些优质网站与工具</p>
    </div>

    <div v-if="loading" class="state-text">
      加载中...
    </div>

    <div v-else-if="error" class="state-text error">
      {{ error }}
    </div>

    <div v-else-if="!links.length" class="state-text">
      暂无资源链接
    </div>

    <div v-else class="card-grid">
      <a
        v-for="link in links"
        :key="link.id"
        class="link-card"
        :style="{ borderTopColor: link.color || '#3b82f6' }"
        :href="link.url"
        target="_blank"
        rel="noopener noreferrer"
      >
        <div
          class="card-avatar"
          :style="{ background: link.color || '#3b82f6' }"
        >
          <img
            v-if="link.image_url"
            :src="link.image_url"
            :alt="link.name"
            loading="lazy"
          />

          <span v-else class="avatar-text">
            {{ avatarLetter(link.name) }}
          </span>
        </div>

        <h3 class="card-title">
          {{ link.name }}
        </h3>

        <p
          v-if="link.description"
          class="card-desc"
        >
          {{ link.description }}
        </p>
      </a>
    </div>
  </div>
</template>

<style scoped>
.resource-page {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;

  padding-top: calc(var(--navbar-height) + 32px);
  padding-bottom: 48px;
  padding-left: 24px;
  padding-right: 24px;

  box-sizing: border-box;
}

.page-header {
  text-align: center;
  margin-bottom: 40px;
}

.page-header h1 {
  margin: 0;
  font-size: 2rem;
  font-weight: 700;
  color: var(--color-text);
}

.page-header p {
  margin-top: 12px;
  color: var(--color-text-secondary);
  font-size: 0.95rem;
}

.state-text {
  text-align: center;
  padding: 64px 0;
  color: var(--color-text-secondary);
  font-size: 1rem;
}

.error {
  color: #ef4444;
}

/* =========================
   Grid
========================= */

.card-grid {
  display: grid;

  /* 核心修复 */
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));

  gap: 24px;

  width: 100%;
}

/* 关键修复：允许子元素收缩 */
.card-grid > * {
  min-width: 0;
}

/* =========================
   Card
========================= */

.link-card {
  min-width: 0;

  background: var(--color-surface);

  border-radius: 16px;
  border-top: 4px solid #3b82f6;

  padding: 28px 20px 22px;

  display: flex;
  flex-direction: column;
  align-items: center;

  text-align: center;

  cursor: pointer;

  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease;

  box-shadow: var(--shadow-card);

  overflow: hidden;

  box-sizing: border-box;
}

.link-card:hover {
  transform: translateY(-4px);

  box-shadow: var(--shadow-card-hover);
}

/* =========================
   Avatar
========================= */

.card-avatar {
  width: 82px;
  height: 82px;

  border-radius: 50%;

  overflow: hidden;

  display: flex;
  align-items: center;
  justify-content: center;

  margin-bottom: 18px;

  flex-shrink: 0;
}

.card-avatar img {
  width: 100%;
  height: 100%;

  object-fit: cover;

  display: block;
}

.avatar-text {
  color: #ffffff;

  font-size: 2rem;
  font-weight: 700;

  user-select: none;
}

/* =========================
   Content
========================= */

.card-title {
  width: 100%;

  margin: 0 0 10px;

  font-size: 1.05rem;
  font-weight: 600;

  color: var(--color-text);

  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-desc {
  width: 100%;

  margin: 0;

  font-size: 0.88rem;
  line-height: 1.6;

  color: var(--color-text-secondary);

  overflow: hidden;

  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;

  /* 防止超长文本撑爆布局 */
  word-break: break-word;
  overflow-wrap: break-word;
}

/* =========================
   Mobile
========================= */

@media (max-width: 768px) {
  .resource-page {
    padding-left: 16px;
    padding-right: 16px;
  }

  .card-grid {
    gap: 18px;
  }

  .link-card {
    padding: 24px 16px 18px;
  }
}

@media (max-width: 480px) {
  .page-header h1 {
    font-size: 1.6rem;
  }

  .card-grid {
    grid-template-columns: 1fr;
  }
}
</style>
