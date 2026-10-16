<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { fetchArticleList } from '@/api'
import ArticleCard from '@/components/ArticleCard.vue'
import Pagination from '@/components/Pagination.vue'
import SearchBox from '@/components/SearchBox.vue'
import SidePanel from '@/components/SidePanel.vue'

const BREAKPOINT = 768
const SIDEPANEL_BREAKPOINT = 1200

const isWide = ref(window.innerWidth >= BREAKPOINT)
const showSidePanel = ref(window.innerWidth >= SIDEPANEL_BREAKPOINT)
const mediaSrc = ref(isWide.value ? '/img/咕咕嘎嘎.mp4' : '/img/咕咕嘎嘎.png')
const videoKey = ref(0)
const showVideo = ref(isWide.value)
const showImage = ref(!isWide.value)

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
  const wide = window.innerWidth >= BREAKPOINT
  if (wide !== isWide.value) {
    isWide.value = wide
    if (wide) {
      videoKey.value++
      mediaSrc.value = '/img/咕咕嘎嘎.mp4'
      showVideo.value = true
      showImage.value = false
    } else {
      mediaSrc.value = '/img/咕咕嘎嘎.png'
      showVideo.value = false
      showImage.value = true
    }
  }
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
      <div class="hero-media">
        <video
          v-if="showVideo"
          :key="'v' + videoKey"
          :src="mediaSrc"
          class="hero-video"
          autoplay
          muted
          loop
          playsinline
        ></video>
        <img
          v-show="showImage"
          :src="mediaSrc"
          alt="hero background"
          class="hero-img"
        />
      </div>
      <div class="hero-overlay">
        <h1 class="hero-title">ZDBlog</h1>
        <p class="hero-subtitle">
          {{ subtitleChars }}
          <span class="cursor" :class="{ blink: subtitleChars.length === subtitleText.length }">|</span>
        </p>
      </div>

      <Transition name="fade">
        <button v-show="scrollDownVisible" class="scroll-indicator" @click="scrollToArticles">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
        </button>
      </Transition>
    </section>

    <!-- Article list section -->
    <section ref="articleSection" class="articles-section container-wide">
      <div class="articles-layout">
        <div class="articles-main">
          <SearchBox v-model="searchQuery" @search="onSearch" />

          <div v-if="loading" class="state-text">加载中...</div>
          <div v-else-if="error" class="state-text error">{{ error }}</div>
          <div v-else-if="!articles.length" class="state-text">暂无文章</div>

          <div v-else :class="['card-grid', { 'card-grid-2col': isWide }]">
            <ArticleCard
              v-for="(article, i) in articles"
              :key="article.id"
              :article="article"
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
  height: 100vh;
  min-height: 500px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 30%;
  background: linear-gradient(to bottom, transparent 0%, rgba(0,0,0,0.25) 80%, var(--color-bg) 100%);
  z-index: 1;
  pointer-events: none;
}

.hero-overlay {
  position: relative;
  z-index: 1;
  text-align: center;
  color: #fff;
  text-shadow: 0 2px 12px rgba(0,0,0,0.5);
  pointer-events: none;
  transform: translateY(-20%);
}

.hero-media {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.hero-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  animation: mediaIn 0.5s ease-out;
}

.hero-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  animation: mediaIn 0.5s ease-out;
}

@keyframes mediaIn {
  from { opacity: 0.4; }
  to { opacity: 1; }
}

.hero-title {
  font-size: clamp(2.4rem, 6vw, 4.2rem);
  font-weight: 800;
  letter-spacing: 0.04em;
  margin-bottom: 0.3em;
}

.hero-subtitle {
  font-family: 'STKaiti', 'KaiTi', '楷体', 'Noto Serif SC', serif;
  font-size: clamp(1.15rem, 2.2vw, 1.45rem);
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
  z-index: 1;
  background: rgba(255,255,255,0.2);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(255,255,255,0.3);
  border-radius: 50%;
  width: 44px;
  height: 44px;
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
  position: relative;
  z-index: 2;
  /* margin-top: -60px; */
  padding-top: 60px;
  padding-bottom: 64px;
  background: linear-gradient(to bottom, transparent 0%, var(--color-bg) 60px);
}

.articles-layout {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

.articles-main {
  flex: 1;
  min-width: 0;
}

.card-grid {
  display: grid;
  gap: 20px;
  grid-template-columns: 1fr;
}

.card-grid-2col {
  grid-template-columns: repeat(2, 1fr);
}

.state-text {
  text-align: center;
  color: var(--color-text-secondary);
  padding: 48px 0;
  font-size: 0.95rem;
}
.error { color: #ef4444; }
</style>
