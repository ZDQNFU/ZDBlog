<script setup>
import { ref, onMounted, watch, nextTick, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchArticleList } from '@/api'
import ArticleCard from '@/components/ArticleCard.vue'
import Pagination from '@/components/Pagination.vue'
import SearchBox from '@/components/SearchBox.vue'
import SidePanel from '@/components/SidePanel.vue'

const route = useRoute()
const router = useRouter()

const SIDEPANEL_BREAKPOINT = 1200
const showSidePanel = ref(window.innerWidth >= SIDEPANEL_BREAKPOINT)

const articles = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const error = ref('')
const searchQuery = ref(route.query.search || '')

let observer = null

function onResize() {
  showSidePanel.value = window.innerWidth >= SIDEPANEL_BREAKPOINT
}

function setupObserver() {
  if (observer) observer.disconnect()
  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible')
        }
      })
    },
    { threshold: 0.12 },
  )
  document.querySelectorAll('.fade-up').forEach((el) => observer.observe(el))
}

async function load(page) {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchArticleList(page, pageSize.value, searchQuery.value)
    articles.value = data.results
    total.value = data.count
    currentPage.value = page
  } catch (e) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
  await nextTick()
  setupObserver()
}

function onSearch(val) {
  searchQuery.value = val
  router.push({ query: { search: val || undefined, page: 1 } })
}

function onPageChange(page) {
  router.push({ query: { search: searchQuery.value || undefined, page } })
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(() => {
  window.addEventListener('resize', onResize)
  const p = Number(route.query.page) || 1
  load(p)
})

watch(
  () => ({ page: route.query.page, search: route.query.search }),
  ({ page, search }) => {
    searchQuery.value = search || ''
    load(Number(page) || 1)
  },
)

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  if (observer) observer.disconnect()
})
</script>

<template>
  <div class="article-list-page container-wide">
    <div class="articles-layout">
      <div class="articles-main">
        <header class="page-header">
          <p class="section-eyebrow">把想法写下来，让探索有迹可循</p>
          <div class="section-heading"><h1>文章归档<span v-if="total" class="article-count">{{ total }} 篇文章</span></h1><router-link class="archive-link" to="/">返回首页 ↗</router-link></div>
        </header>

        <SearchBox v-model="searchQuery" @search="onSearch" />

        <div v-if="loading" class="state-text">加载中...</div>
        <div v-else-if="error" class="state-text error">{{ error }}</div>
        <div v-else-if="!articles.length" class="state-text">暂无文章</div>

        <div v-else class="card-grid">
          <ArticleCard
            v-for="(article, i) in articles"
            :key="article.id"
            :article="article"
            :reverse-cut="i % 2 === 1"
            class="fade-up"
            :style="{ transitionDelay: i * 0.08 + 's' }"
          />
        </div>

        <Pagination
          :current="currentPage"
          :total="total"
          :page-size="pageSize"
          @change="onPageChange"
        />
      </div>

      <SidePanel v-if="showSidePanel" />
    </div>
  </div>
</template>

<style scoped>
.article-list-page {
  padding-top: calc(var(--navbar-height) + 44px);
  padding-bottom: 48px;
}

.articles-layout {
  display: flex;
  gap: 28px;
  align-items: flex-start;
}

.articles-main {
  flex: 1;
  min-width: 0;
}

.page-header { padding: 22px 24px 0; margin-bottom: 20px; border-radius: 16px; background: var(--floating-surface); box-shadow: var(--shadow-card); overflow: hidden; }
.page-header h1 {
  font-size: 1.8rem;
  font-weight: 700;
  margin-bottom: 0;
}

.card-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 24px;
}

.state-text {
  text-align: center;
  color: var(--color-text-secondary);
  padding: 48px 0;
  font-size: 0.95rem;
}
.error { color: #ef4444; }
@media (max-width: 767px) {
  .article-list-page { padding-top: calc(var(--navbar-height) + 28px); }
  .card-grid { grid-template-columns: 1fr; gap: 18px; }
  .page-header h1 { font-size: 1.4rem; }
}
</style>
