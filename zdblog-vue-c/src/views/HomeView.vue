<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { fetchArticleList } from '@/api'
import ArticleCard from '@/components/ArticleCard.vue'
import Pagination from '@/components/Pagination.vue'
import SearchBox from '@/components/SearchBox.vue'
import SidePanel from '@/components/SidePanel.vue'

const SIDEPANEL_BREAKPOINT = 1200

const showSidePanel = ref(window.innerWidth >= SIDEPANEL_BREAKPOINT)

const articles = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const error = ref('')
const articleSection = ref(null)
const searchQuery = ref('')

const scrollDownVisible = ref(true)

// typewriter effect for subtitle
const subtitleText = '用文字记录技术与生活'
const subtitleChars = ref('')
let typewriterTimer = null

function startTypewriter() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    subtitleChars.value = subtitleText
    return
  }
  let i = 0
  subtitleChars.value = ''
  typewriterTimer = setInterval(() => {
    if (i < subtitleText.length) {
      subtitleChars.value += subtitleText[i]
      i++
    } else {
      clearInterval(typewriterTimer)
      typewriterTimer = null
    }
  }, 150)
}

let observer = null

function onResize() {
  showSidePanel.value = window.innerWidth >= SIDEPANEL_BREAKPOINT
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
  currentPage.value = 1
  load(1)
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

function onScroll() {
  scrollDownVisible.value = window.scrollY < 100
}

function scrollToArticles() {
  articleSection.value?.scrollIntoView({ behavior: 'smooth' })
}

function onPageChange(page) {
  currentPage.value = page
  load(page)
  articleSection.value?.scrollIntoView({ behavior: 'smooth' })
}

onMounted(() => {
  window.addEventListener('resize', onResize)
  window.addEventListener('scroll', onScroll, { passive: true })
  startTypewriter()
  load(1)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('scroll', onScroll)
  if (observer) observer.disconnect()
  if (typewriterTimer) clearInterval(typewriterTimer)
})
</script>

<template>
  <div class="home">
    <!-- Hero -->
    <section class="hero">
      <div class="hero-overlay container-wide">
        <p class="hero-eyebrow">ZD 的个人博客</p>
        <h1 class="hero-title">在这里，<br />记录每一份<span>探索。</span></h1>
        <p class="hero-subtitle">
          {{ subtitleChars }}
          <span class="cursor" :class="{ blink: subtitleChars.length === subtitleText.length }">|</span>
        </p>
        <div class="hero-actions">
          <button class="hero-primary" @click="scrollToArticles">开始阅读 <span aria-hidden="true">↗</span></button>
          <router-link to="/message-board" class="hero-secondary">留下足迹 <span aria-hidden="true">→</span></router-link>
        </div>
      </div>

      <Transition name="fade">
        <button v-show="scrollDownVisible" class="scroll-indicator" @click="scrollToArticles" aria-label="浏览最新文章">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
        </button>
      </Transition>
    </section>

    <!-- Article list section -->
    <section ref="articleSection" class="articles-section container-wide">
      <div class="section-heading">
        <div><p class="section-eyebrow">文字里的小世界</p><h2>最近更新<span v-if="total" class="article-count">{{ total }} 篇文章</span></h2></div>
        <router-link class="archive-link" to="/articles">全部文章 ↗</router-link>
      </div>
      <div class="articles-layout">
        <div class="articles-main">
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
    </section>
  </div>
</template>

<style scoped>
/* ---------- Hero ---------- */
.hero {
  position: relative;
  width: 100%;
  height: 100svh;
  min-height: 560px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}


.hero-overlay {
  position: relative;
  z-index: 2;
  width: 100%;
  text-align: left;
  color: #fff;
  text-shadow: 0 2px 12px rgba(0,0,0,0.5);
  padding-top: var(--navbar-height);
  padding-bottom: 30px;
}

.hero-title {
  font-size: clamp(2.8rem, 4.6vw, 4.4rem);
  font-weight: 750;
  letter-spacing: .025em;
  line-height: 1.3;
  margin-bottom: 24px;
}

.hero-subtitle {
  font-size: 1.05rem;
  opacity: 0.92;
  letter-spacing: 0.08em;
}

.cursor {
  font-weight: 300;
  color: rgba(255,255,255,0.9);
}
.cursor.blink {
  animation: blink 0.8s step-end infinite;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* scroll indicator */
.scroll-indicator {
  position: absolute;
  bottom: 28px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2;
  background: rgba(255,255,255,0.2);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(255,255,255,0.3);
  border-radius: 50%;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #fff;
  animation: bounce 2s ease-in-out infinite;
  transition: background 0.2s;
}
.scroll-indicator:hover {
  background: rgba(255,255,255,0.35);
}

@keyframes bounce {
  0%, 100% { transform: translateX(-50%) translateY(0); }
  50% { transform: translateX(-50%) translateY(8px); }
}

.fade-leave-active {
  transition: opacity 0.3s;
}
.fade-leave-to {
  opacity: 0;
}

/* ---------- Article section ---------- */
.articles-section {
  scroll-margin-top: calc(var(--navbar-height) + 20px);
  position: relative;
  z-index: 2;
  padding-top: 44px;
  padding-bottom: 64px;
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

.card-grid {
  display: grid;
  gap: 24px;
  grid-template-columns: 1fr;
}


.state-text {
  text-align: center;
  color: var(--color-text-secondary);
  padding: 48px 0;
  font-size: 0.95rem;
}
.error { color: #ef4444; }
.section-heading { padding: 20px 24px; border-radius: 16px; background: var(--floating-surface); box-shadow: var(--shadow-card); }
.hero-title span { color: #f9dc92; }
.hero-eyebrow { font-size: .85rem; font-weight: 600; letter-spacing: .18em; margin-bottom: 24px; }
.hero-actions { display: flex; gap: 28px; align-items: center; margin-top: 32px; font-size: .9rem; text-shadow: none; }
.hero-primary { border: none; border-radius: 999px; padding: 13px 23px; background: white; color: #254351; font: inherit; font-weight: 650; cursor: pointer; transition: transform .2s; }
.hero-primary:hover { transform: translateY(-3px); }
.hero-primary span { margin-left: 20px; }
.hero-secondary { padding: 12px 0; border-bottom: 1px solid #ffffff70; }
.hero-secondary span { margin-left: 12px; }
@media (max-width: 767px) {
  .hero { height: 100svh; min-height: 550px; }
  .hero-overlay { padding-left: 26px; padding-bottom: clamp(190px, 32svh, 270px); }
  .hero-title { font-size: clamp(2rem, 9.8vw, 3.5rem); margin-bottom: 18px; }
  .hero-eyebrow { margin-bottom: 18px; font-size: .75rem; }
  .hero-subtitle { font-size: .9rem; }
  .hero-actions { margin-top: 24px; gap: 22px; font-size: .83rem; }
  .articles-section { padding-top: 30px; padding-bottom: 36px; scroll-margin-top: var(--navbar-height); }
}
@media (max-width: 1100px) { .side-panel { display: none; } }
</style>
