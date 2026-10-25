<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { fetchRandomArticles, fetchTags } from '@/api'

const router = useRouter()
const recommended = ref([])
const tags = ref([])
const countFormatter = new Intl.NumberFormat('zh-CN', { notation: 'compact', maximumFractionDigits: 1 })

function goTag(tag) {
  router.push({ path: '/articles', query: { search: tag.name } })
}

onMounted(async () => {
  const [recRes, tagRes] = await Promise.all([
    fetchRandomArticles().catch(() => []),
    fetchTags().catch(() => []),
  ])
  recommended.value = (Array.isArray(recRes) ? recRes : (recRes.results || [])).slice(0, 3)
  tags.value = Array.isArray(tagRes) ? tagRes : (tagRes.results || [])
})
</script>

<template>
  <aside class="side-panel" aria-label="文章探索">
    <section v-if="recommended.length" class="panel-section" aria-labelledby="recommended-heading">
      <header class="panel-header">
        <h2 id="recommended-heading" class="panel-title">推荐文章</h2>
        <span class="panel-count">{{ recommended.length }} 篇</span>
      </header>
      <div class="rec-list">
        <router-link v-for="(item, index) in recommended" :key="item.id" :to="`/article/${item.id}`" class="rec-item">
          <div class="rec-cover" :class="{ 'rec-cover-empty': !item.cover }" aria-hidden="true">
            <img v-if="item.cover" :src="item.cover" alt="" loading="lazy" decoding="async" />
            <span v-else>{{ String(index + 1).padStart(2, '0') }}</span>
          </div>
          <div class="rec-body">
            <span class="rec-title">{{ item.title }}</span>
            <span class="rec-meta">
              <span v-if="item.category?.name" class="rec-category">{{ item.category.name }}</span>
              <span>{{ countFormatter.format(item.view_count || 0) }} 阅读</span>
            </span>
          </div>
        </router-link>
      </div>
    </section>

    <section v-if="tags.length" class="panel-section" aria-labelledby="tags-heading">
      <header class="panel-header">
        <h2 id="tags-heading" class="panel-title">标签云</h2>
        <span class="panel-count">{{ tags.length }} 个</span>
      </header>
      <div class="tag-cloud">
        <button v-for="tag in tags" :key="tag.id" type="button" class="tag-link"
          :style="{ '--tag-color': tag.color || 'var(--color-primary)' }" :title="tag.name" @click="goTag(tag)">
          <span class="tag-hash" aria-hidden="true">#</span><span class="tag-name">{{ tag.name }}</span>
        </button>
      </div>
    </section>
  </aside>
</template>

<style scoped>
.side-panel {
  flex: 0 0 280px;
  width: 280px;
  position: sticky;
  top: calc(var(--navbar-height) + 24px);
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.panel-section {
  padding: 18px;
  border: 1px solid var(--color-border);
  border-radius: 16px;
  background: var(--floating-surface);
  box-shadow: var(--shadow-card);
}
.panel-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.panel-title { display: flex; align-items: center; gap: 8px; font-size: .88rem; line-height: 1.5; font-weight: 650; color: var(--color-text); }
.panel-title::before { content: ''; width: 3px; height: 13px; border-radius: 2px; background: var(--color-primary); }
.panel-count { font-size: .67rem; color: var(--color-text-secondary); font-variant-numeric: tabular-nums; }
.rec-list { display: flex; flex-direction: column; }
.rec-item { display: flex; align-items: center; gap: 12px; min-width: 0; padding: 11px 0; border-bottom: 1px solid var(--color-border); color: var(--color-text); }
.rec-item:first-child { padding-top: 0; }
.rec-item:last-child { padding-bottom: 0; border-bottom: 0; }
.rec-cover { width: 58px; height: 52px; flex-shrink: 0; overflow: hidden; border-radius: 8px; background: color-mix(in srgb, var(--color-primary) 8%, var(--color-surface)); }
.rec-cover img { display: block; width: 100%; height: 100%; object-fit: cover; transition: transform .3s; }
.rec-cover-empty { display: grid; place-items: center; color: var(--color-primary); font-size: 1.15rem; font-weight: 600; font-variant-numeric: tabular-nums; }
.rec-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 5px; }
.rec-title { font-size: .81rem; font-weight: 550; line-height: 1.5; overflow: hidden; overflow-wrap: anywhere; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; transition: color .2s; }
.rec-item:hover .rec-title { color: var(--color-primary); }
.rec-item:hover img { transform: scale(1.06); }
.rec-meta { display: flex; align-items: center; gap: 8px; min-width: 0; color: var(--color-text-secondary); font-size: .65rem; line-height: 1.4; }
.rec-meta > span { white-space: nowrap; }
.rec-category { max-width: 70px; overflow: hidden; text-overflow: ellipsis; }
.rec-category::after { content: '·'; margin-left: 8px; opacity: .6; }
.tag-cloud { display: flex; flex-wrap: wrap; gap: 7px; }
.tag-link { display: inline-flex; align-items: center; gap: 5px; min-width: 0; max-width: 100%; padding: 5px 9px; border: 1px solid color-mix(in srgb, var(--tag-color) 16%, transparent); border-radius: 7px; background: color-mix(in srgb, var(--tag-color) 6%, transparent); color: var(--color-text); font: inherit; font-size: .74rem; line-height: 1.5; cursor: pointer; transition: background .2s, border-color .2s, color .2s; }
.tag-hash { color: var(--tag-color); font-weight: 650; opacity: .8; }
.tag-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tag-link:hover { background: color-mix(in srgb, var(--tag-color) 14%, transparent); border-color: color-mix(in srgb, var(--tag-color) 38%, transparent); color: var(--color-primary); }
</style>
