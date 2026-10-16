<script setup>
import { ref, computed, onMounted, nextTick, watch, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { fetchStats } from '@/api/auth'
import { fetchVisitorGeo } from '@/api/tracking'
import { useTheme } from '@/composables/useTheme'
import ArticleMarkdownImport from '@/components/ArticleMarkdownImport.vue'
import { Bar, Pie, Doughnut, Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement, PointElement, LineElement, Title, Tooltip, Legend,
  ArcElement, Filler,
} from 'chart.js'
import * as echarts from 'echarts'
import chinaGeoJSON from '@/assets/china.json'

echarts.registerMap('china', chinaGeoJSON)

ChartJS.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, Title, Tooltip, Legend, ArcElement, Filler)

const { isDark } = useTheme()
const router = useRouter()
const todayLabel = computed(() => new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric', month: 'long', day: 'numeric', weekday: 'long',
}).format(new Date()))

const stats = ref(null)
const loading = ref(false)
const geoData = ref([])
const geoLoading = ref(true)
const geoError = ref(false)
const geoErrorDetail = ref('')
const geoSummary = ref({})
const geoEmptyReason = ref(null)
const geoEmptyTitle = computed(() => {
  if (geoEmptyReason.value === 'no_public_ips') return '近 30 日没有可定位的公网访客 IP'
  if (geoEmptyReason.value === 'no_china_locations') return '近 30 日暂无可展示的国内地域'
  return '近 30 日暂无访客记录'
})
const geoEmptyDescription = computed(() => {
  const summary = geoSummary.value
  if (geoEmptyReason.value === 'no_public_ips') {
    const testHint = summary.benchmark_ips ? `，其中 ${summary.benchmark_ips} 个为性能测试保留地址` : ''
    return `检测到 ${summary.total_ips || 0} 个内网、保留或无效 IP${testHint}；这些地址没有真实公网地域。`
  }
  if (geoEmptyReason.value === 'no_china_locations') {
    return `已查询 ${summary.queried_ips || 0} 个公网 IP，离线库未返回可在中国地图展示的省份。`
  }
  return '公网访客访问后将在地图上显示。'
})
const geoChartRef = ref(null)
let geoChart = null

const countRefs = ref({})

function animateCount(key, target) {
  const el = countRefs.value[key]
  if (!el || target == null) return
  const duration = 900
  const start = performance.now()
  const from = 0
  function step(now) {
    const progress = Math.min((now - start) / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    el.textContent = Math.round(from + eased * (target - from))
    if (progress < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

function triggerCountUp() {
  if (!stats.value) return
  const totals = stats.value.totals
  const keys = ['articles', 'published', 'draft', 'private', 'tags', 'categories', 'comments', 'views', 'likes']
  keys.forEach(k => {
    if (totals[k] != null) animateCount(k, totals[k])
  })
}

watch(stats, (val) => {
  if (val) {
    nextTick(() => triggerCountUp())
  }
})

async function load() {
  loading.value = true
  try {
    const statsRes = await fetchStats()
    stats.value = statsRes.data
  } finally {
    loading.value = false
  }
}

async function loadGeo() {
  geoLoading.value = true
  geoError.value = false
  geoErrorDetail.value = ''
  try {
    const { data } = await fetchVisitorGeo()
    geoData.value = data.points || []
    geoSummary.value = data.summary || {}
    geoEmptyReason.value = data.empty_reason || null
  } catch (error) {
    geoError.value = true
    geoErrorDetail.value = error.response?.data?.detail || '请求未成功，请稍后重试。'
  } finally {
    geoLoading.value = false
  }
}

function initGeoChart() {
  if (!geoChartRef.value || !geoData.value.length) return
  if (geoChart) geoChart.dispose()
  geoChart = echarts.init(geoChartRef.value)

  const points = geoData.value.map(p => ({
    value: [p.lon, p.lat],
    name: p.ip,
    city: p.city,
    country: p.country,
  }))

  const dark = isDark.value

  geoChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter(p) {
        if (p.seriesType === 'scatter') {
          const d = p.data
          return `<strong>${d.name}</strong><br/>${d.city}, ${d.country}`
        }
        return p.name
      },
    },
    geo: {
      map: 'china',
      roam: true,
      zoom: 1.2,
      center: [104.5, 36],
      itemStyle: {
        areaColor: dark ? '#1e293b' : '#f0f5ff',
        borderColor: dark ? '#475569' : '#b0c4de',
        borderWidth: 0.5,
      },
      emphasis: {
        itemStyle: { areaColor: '#409eff33' },
        label: { show: true, color: dark ? '#e2e8f0' : '#333' },
      },
      label: { show: false },
    },
    series: [{
      type: 'scatter',
      coordinateSystem: 'geo',
      data: points,
      symbolSize: (val) => Math.min(Math.max(points.length / 2, 6), 14),
      itemStyle: {
        color: '#409eff',
        shadowBlur: 8,
        shadowColor: 'rgba(64,158,255,0.5)',
      },
      emphasis: {
        itemStyle: { color: '#f56c6c', shadowBlur: 16, shadowColor: 'rgba(245,108,108,0.6)' },
      },
    }],
  })
}

watch(geoData, async (val) => {
  if (val.length) {
    await nextTick()
    initGeoChart()
  }
})

watch(isDark, () => {
  if (geoData.value.length) initGeoChart()
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  color: isDark.value ? '#a9b8cc' : '#68778b',
  scales: {
    x: { ticks: { color: isDark.value ? '#91a2b8' : '#77859a' }, grid: { color: isDark.value ? 'rgba(137,160,190,.10)' : 'rgba(84,105,132,.10)' } },
    y: { ticks: { color: isDark.value ? '#91a2b8' : '#77859a' }, grid: { color: isDark.value ? 'rgba(137,160,190,.10)' : 'rgba(84,105,132,.10)' } },
  },
  plugins: {
    legend: { position: 'bottom', labels: { color: isDark.value ? '#a9b8cc' : '#68778b', padding: 20, usePointStyle: true, pointStyleWidth: 8 } },
    tooltip: { backgroundColor: isDark.value ? '#101a29' : '#17263a', titleColor: '#fff', bodyColor: '#d8e4f1', padding: 12, cornerRadius: 8 },
  },
}))

onMounted(() => {
  load()
  loadGeo()
})

function resizeGeoChart() {
  geoChart?.resize()
}

window.addEventListener('resize', resizeGeoChart)

onUnmounted(() => {
  window.removeEventListener('resize', resizeGeoChart)
  if (geoChart) { geoChart.dispose(); geoChart = null }
})

const statCards = [
  { key: 'articles', label: '文章总数', icon: 'articles', color: '#409eff' },
  { key: 'published', label: '已发布', icon: 'published', color: '#22c55e' },
  { key: 'draft', label: '草稿', icon: 'draft', color: '#f59e0b' },
  { key: 'private', label: '私密', icon: 'private', color: '#f56c6c' },
  { key: 'tags', label: '标签', icon: 'tags', color: '#8b5cf6' },
  { key: 'categories', label: '分类', icon: 'categories', color: '#06b6d4' },
  { key: 'comments', label: '评论', icon: 'comments', color: '#ec4899' },
  { key: 'views', label: '总浏览', icon: 'views', color: '#f97316' },
  { key: 'likes', label: '总点赞', icon: 'likes', color: '#ef4444' },
]
</script>

<template>
  <div class="dashboard">
    <section class="dashboard-intro">
      <div class="intro-copy">
        <div class="eyebrow"><span class="eyebrow-line"></span> ZDBLOG / CONTROL DECK</div>
        <h1>内容观测台<span class="title-period">.</span></h1>
        <p>内容、访问与互动数据的实时概览</p>
      </div>
      <div class="intro-side">
        <div class="date-stamp"><span class="date-dot"></span>{{ todayLabel }}</div>
        <div class="quick-actions">
          <ArticleMarkdownImport variant="dashboard" />
          <button class="action-secondary" @click="router.push('/articles')">
            <el-icon><Document /></el-icon>文章管理
          </button>
          <button class="action-primary" @click="router.push('/articles/edit')">
            <el-icon><Plus /></el-icon>新建文章
          </button>
        </div>
      </div>
      <div class="intro-orbit orbit-one"></div>
      <div class="intro-orbit orbit-two"></div>
    </section>

    <div v-if="loading" class="loading-skeleton">
      <div v-for="i in 9" :key="i" class="skeleton-card"></div>
    </div>

    <template v-else-if="stats">
      <section class="section-block metrics-block">
        <div class="section-heading">
          <div><span class="section-kicker">SYSTEM SNAPSHOT</span><h2>核心指标</h2></div>
          <span class="live-state"><i></i> 数据已同步</span>
        </div>
        <div class="stats-row">
        <div
          v-for="card in statCards"
          :key="card.key"
          class="stat-card"
          :style="{ '--accent': card.color }"
        >
          <div class="stat-icon">
            <!-- Articles -->
            <svg v-if="card.icon === 'articles'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
            <!-- Published -->
            <svg v-else-if="card.icon === 'published'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            <!-- Draft -->
            <svg v-else-if="card.icon === 'draft'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            <!-- Private -->
            <svg v-else-if="card.icon === 'private'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/><circle cx="12" cy="16" r="1"/></svg>
            <!-- Tags -->
            <svg v-else-if="card.icon === 'tags'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
            <!-- Categories -->
            <svg v-else-if="card.icon === 'categories'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
            <!-- Comments -->
            <svg v-else-if="card.icon === 'comments'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><line x1="8" y1="9" x2="16" y2="9"/><line x1="8" y1="13" x2="14" y2="13"/></svg>
            <!-- Views -->
            <svg v-else-if="card.icon === 'views'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
            <!-- Likes -->
            <svg v-else-if="card.icon === 'likes'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
          </div>
          <div class="stat-body">
            <span :ref="el => countRefs[card.key] = el" class="stat-num">0</span>
            <span class="stat-label">{{ card.label }}</span>
          </div>
          <span class="stat-index">{{ String(statCards.indexOf(card) + 1).padStart(2, '0') }}</span>
        </div>
        </div>
      </section>

      <section class="section-block insights-block">
        <div class="section-heading">
          <div><span class="section-kicker">AUDIENCE / CONTENT</span><h2>访问与内容</h2></div>
          <span class="section-caption">基于近期站点数据</span>
        </div>
        <div class="dual-row">
        <div class="panel map-panel">
          <div class="panel-heading">
            <div><span class="panel-code">01 / GEO NETWORK · 30 DAYS</span><h3 class="panel-title">近 30 日访客地域分布</h3></div>
            <span class="panel-count">{{ geoData.length }} <small>个来源点</small></span>
          </div>
          <div v-if="geoData.length" class="map-container" ref="geoChartRef"></div>
          <div v-else class="map-empty">
            <span class="empty-mark">⌁</span>
            <span v-if="geoLoading">正在查询近 30 日访客地域…</span>
            <span v-else-if="geoError">访客地域暂时无法加载</span>
            <span v-else>{{ geoEmptyTitle }}</span>
            <small v-if="geoError">{{ geoErrorDetail }}</small>
            <small v-if="geoError"><button class="geo-retry" type="button" @click="loadGeo">点击重试</button></small>
            <small v-else-if="geoLoading">正在读取本地地域库</small>
            <small v-else>{{ geoEmptyDescription }}</small>
          </div>
        </div>
        <div class="panel chart-panel">
          <div class="panel-heading">
            <div><span class="panel-code">02 / CONTENT MIX</span><h3 class="panel-title">文章状态分布</h3></div>
          </div>
          <div class="chart-wrapper">
            <Doughnut
              :data="{
                labels: ['已发布', '草稿', '私密'],
                datasets: [{
                  data: [stats.totals.published, stats.totals.draft, stats.totals.private],
                  backgroundColor: ['#22c55e', '#f59e0b', '#f56c6c'],
                  borderWidth: 0,
                  borderRadius: 4,
                }]
              }"
              :options="chartOptions"
            />
          </div>
        </div>
        </div>
      </section>

      <section class="section-block analytics-block">
        <div class="section-heading">
          <div><span class="section-kicker">PUBLISHING ANALYTICS</span><h2>内容分析</h2></div>
          <span class="section-caption">分类、标签与发布节奏</span>
        </div>
        <div class="charts-grid">
        <div class="panel chart-panel">
          <div class="panel-heading"><div><span class="panel-code">03 / TAG RANKING</span><h3 class="panel-title">标签文章数 <small>TOP 10</small></h3></div></div>
          <div class="chart-wrapper">
            <Bar
              :data="{
                labels: stats.tag_stats?.map(t => t.name) || [],
                datasets: [{
                  label: '文章数',
                  data: stats.tag_stats?.map(t => t.article_count) || [],
                  backgroundColor: stats.tag_stats?.map(t => t.color + '99') || [],
                  borderColor: stats.tag_stats?.map(t => t.color) || [],
                  borderWidth: 2,
                  borderRadius: 6,
                  borderSkipped: false,
                }]
              }"
              :options="{ ...chartOptions, plugins: { ...chartOptions.plugins, legend: { display: false } } }"
            />
          </div>
        </div>

        <div class="panel chart-panel">
          <div class="panel-heading"><div><span class="panel-code">04 / CATEGORY MIX</span><h3 class="panel-title">分类文章数</h3></div></div>
          <div class="chart-wrapper">
            <Pie
              :data="{
                labels: stats.category_stats?.map(c => c.name) || [],
                datasets: [{
                  data: stats.category_stats?.map(c => c.article_count) || [],
                  backgroundColor: ['#409eff', '#22c55e', '#f59e0b', '#f56c6c', '#8b5cf6', '#06b6d4', '#ec4899', '#f97316'],
                  borderWidth: 0,
                }]
              }"
              :options="chartOptions"
            />
          </div>
        </div>

        <div class="panel chart-panel" v-if="stats.monthly_trend?.length">
          <div class="panel-heading"><div><span class="panel-code">05 / PUBLISHING PACE</span><h3 class="panel-title">近 6 月发布趋势</h3></div></div>
          <div class="chart-wrapper">
            <Line
              :data="{
                labels: stats.monthly_trend.map(m => m.month?.substring(0, 7)),
                datasets: [{
                  label: '发布数',
                  data: stats.monthly_trend.map(m => m.count),
                  borderColor: '#409eff',
                  backgroundColor: (ctx) => {
                    const g = ctx.chart.ctx.createLinearGradient(0, 0, 0, 260)
                    g.addColorStop(0, 'rgba(64,158,255,0.25)')
                    g.addColorStop(1, 'rgba(64,158,255,0.02)')
                    return g
                  },
                  borderWidth: 2.5,
                  pointBackgroundColor: '#409eff',
                  pointBorderColor: '#fff',
                  pointBorderWidth: 2,
                  pointRadius: 5,
                  pointHoverRadius: 7,
                  fill: true,
                  tension: 0.35,
                }]
              }"
              :options="chartOptions"
            />
          </div>
        </div>

        <div class="panel chart-panel" v-else>
          <div class="panel-heading"><div><span class="panel-code">05 / PUBLISHING PACE</span><h3 class="panel-title">近 6 月发布趋势</h3></div></div>
          <div class="chart-empty">暂无数据</div>
        </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.dashboard { --dash-accent: #2e83d5; --dash-cyan: #25b8c9; --dash-line: color-mix(in srgb, var(--color-border) 78%, transparent); padding-bottom: 36px; }
.dashboard-intro {
  position: relative; isolation: isolate; overflow: hidden; display: flex; align-items: flex-end; justify-content: space-between; gap: 24px;
  min-height: 190px; margin-bottom: 30px; padding: 32px 36px; border: 1px solid var(--dash-line); border-radius: 14px;
  background: linear-gradient(112deg, color-mix(in srgb, var(--color-surface) 96%, #dceeff) 0%, var(--color-surface) 57%, color-mix(in srgb, var(--color-surface) 88%, #bcecf0) 100%);
  box-shadow: 0 10px 30px rgba(27, 59, 91, .055);
}
.dashboard-intro::before { content: ''; position: absolute; z-index: -1; inset: 0; opacity: .32; background-image: linear-gradient(rgba(63, 132, 185, .08) 1px, transparent 1px), linear-gradient(90deg, rgba(63, 132, 185, .08) 1px, transparent 1px); background-size: 28px 28px; mask-image: linear-gradient(90deg, transparent, #000 48%, #000); }
.dashboard-intro::after { content: ''; position: absolute; z-index: -1; right: 16%; top: -165px; width: 360px; height: 360px; border: 1px solid rgba(46, 131, 213, .16); border-radius: 50%; box-shadow: 0 0 0 24px rgba(46, 131, 213, .025), 0 0 0 56px rgba(46, 131, 213, .02); }
.intro-copy, .intro-side { position: relative; z-index: 1; }
.eyebrow, .section-kicker, .panel-code { color: var(--color-text-secondary); font-size: .67rem; font-weight: 700; letter-spacing: .13em; }
.eyebrow { display: flex; align-items: center; gap: 9px; color: var(--dash-accent); }
.eyebrow-line { width: 20px; height: 1px; background: currentColor; }
.intro-copy h1 { margin: 13px 0 8px; color: var(--color-text); font-size: clamp(1.8rem, 3vw, 2.45rem); line-height: 1.12; font-weight: 720; letter-spacing: -.045em; }
.title-period { color: var(--dash-cyan); }
.intro-copy p { color: var(--color-text-secondary); font-size: .93rem; letter-spacing: .015em; }
.intro-side { display: flex; flex-direction: column; align-items: flex-end; gap: 20px; }
.date-stamp { display: flex; align-items: center; gap: 8px; color: var(--color-text-secondary); font-size: .8rem; }
.date-dot, .live-state i { width: 7px; height: 7px; border-radius: 50%; background: #43b982; box-shadow: 0 0 0 4px rgba(67,185,130,.12); }
.quick-actions { display: flex; gap: 9px; }
.quick-actions button { display: inline-flex; align-items: center; justify-content: center; gap: 7px; min-height: 37px; padding: 0 13px; border: 1px solid var(--dash-line); border-radius: 7px; font: inherit; font-size: .8rem; font-weight: 600; cursor: pointer; transition: .18s ease; }
.action-secondary { color: var(--color-text); background: var(--color-surface); }
.action-secondary:hover { border-color: var(--dash-accent); color: var(--dash-accent); }
.action-primary { color: #fff; background: var(--dash-accent); border-color: var(--dash-accent) !important; box-shadow: 0 5px 14px rgba(46,131,213,.2); }
.action-primary:hover { background: #216fb9; transform: translateY(-1px); }
.intro-orbit { display: none; }
.section-block { margin-top: 28px; }
.section-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin-bottom: 14px; }
.section-heading h2 { margin-top: 4px; color: var(--color-text); font-size: 1.06rem; font-weight: 680; letter-spacing: -.02em; }
.section-caption { padding-bottom: 2px; color: var(--color-text-secondary); font-size: .76rem; }
.live-state { display: inline-flex; align-items: center; gap: 8px; padding-bottom: 2px; color: var(--color-text-secondary); font-size: .75rem; }
.live-state i { width: 6px; height: 6px; }
.loading-skeleton { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 12px; }
.skeleton-card { height: 88px; border: 1px solid var(--dash-line); border-radius: 9px; background: var(--color-surface); animation: shimmer 1.5s ease-in-out infinite; }
@keyframes shimmer { 0%, 100% { opacity: .52; } 50% { opacity: .88; } }
.stats-row { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 11px; }
.stat-card { position: relative; display: flex; align-items: center; gap: 13px; min-width: 0; padding: 17px 18px; overflow: hidden; border: 1px solid var(--dash-line); border-radius: 9px; background: var(--color-surface); transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease; }
.stat-card::after { content: ''; position: absolute; top: 0; right: 0; width: 52px; height: 2px; background: var(--accent); opacity: .72; }
.stat-card:hover { transform: translateY(-2px); border-color: color-mix(in srgb, var(--accent) 48%, var(--color-border)); box-shadow: 0 8px 22px rgba(27,59,91,.08); }
.stat-icon { width: 39px; height: 39px; flex: 0 0 39px; display: grid; place-items: center; border: 1px solid color-mix(in srgb, var(--accent) 20%, transparent); border-radius: 8px; background: color-mix(in srgb, var(--accent) 9%, var(--color-surface)); color: var(--accent); }
.stat-body { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.stat-num { color: var(--color-text); font-size: 1.45rem; font-weight: 720; line-height: 1.1; font-variant-numeric: tabular-nums; letter-spacing: -.03em; }
.stat-label { color: var(--color-text-secondary); font-size: .76rem; }
.stat-index { position: absolute; right: 11px; bottom: 9px; color: var(--color-text-secondary); opacity: .45; font: 600 .59rem/1 ui-monospace, SFMono-Regular, Consolas, monospace; letter-spacing: .07em; }
.dual-row { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(300px, .9fr); gap: 14px; }
.charts-grid { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 14px; }
.panel { min-width: 0; padding: 18px 20px 15px; border: 1px solid var(--dash-line); border-radius: 9px; background: var(--color-surface); box-shadow: 0 2px 9px rgba(27,59,91,.025); }
.panel-heading { display: flex; align-items: center; justify-content: space-between; min-height: 38px; gap: 12px; }
.panel-title { margin-top: 5px; color: var(--color-text); font-size: .9rem; font-weight: 650; }
.panel-title small { margin-left: 5px; color: var(--color-text-secondary); font-size: .6rem; font-weight: 600; letter-spacing: .08em; }
.panel-count { color: var(--dash-accent); font-size: .94rem; font-weight: 700; font-variant-numeric: tabular-nums; }
.panel-count small { color: var(--color-text-secondary); font-size: .67rem; font-weight: 400; }
.map-container { width: 100%; height: 310px; }
.map-empty { height: 310px; padding: 0 20px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 9px; color: var(--color-text-secondary); font-size: .83rem; text-align: center; line-height: 1.6; }
.map-empty small { font-size: .7rem; opacity: .8; }
.geo-retry { padding: 0; border: 0; color: var(--dash-accent); background: transparent; font: inherit; cursor: pointer; }
.geo-retry:hover { text-decoration: underline; }
.empty-mark { color: var(--dash-cyan); font-size: 2rem; line-height: 1; }
.chart-wrapper { position: relative; height: 265px; margin-top: 8px; }
.chart-empty { height: 265px; display: flex; align-items: center; justify-content: center; color: var(--color-text-secondary); font-size: .8rem; }

[data-theme="dark"] .dashboard-intro { background: var(--color-surface); box-shadow: none; }
[data-theme="dark"] .dashboard-intro::before,
[data-theme="dark"] .dashboard-intro::after { display: none; }
[data-theme="dark"] .stat-card:hover { box-shadow: none; }
[data-theme="dark"] .panel { box-shadow: none; }

@media (max-width: 1200px) {
  .dual-row { grid-template-columns: minmax(0, 1.25fr) minmax(280px, .9fr); }
  .charts-grid { grid-template-columns: repeat(2, minmax(0,1fr)); }
}
@media (max-width: 900px) {
  .dashboard-intro { padding: 27px 26px; }
  .stats-row { grid-template-columns: repeat(3, minmax(0,1fr)); }
  .dual-row { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .dashboard { padding-bottom: 24px; }
  .dashboard-intro { min-height: 0; align-items: flex-start; flex-direction: column; gap: 22px; margin-bottom: 24px; padding: 23px 20px; }
  .dashboard-intro::after { right: -200px; top: -225px; }
  .intro-copy h1 { margin-top: 11px; font-size: 1.8rem; }
  .intro-copy p { font-size: .82rem; }
  .intro-side { width: 100%; align-items: flex-start; gap: 12px; }
  .date-stamp { font-size: .72rem; }
  .quick-actions { width: 100%; }
  .quick-actions button { flex: 1; }
  .section-block { margin-top: 23px; }
  .section-heading { align-items: flex-start; }
  .section-caption { max-width: 42%; text-align: right; font-size: .68rem; }
  .stats-row { grid-template-columns: repeat(2, minmax(0,1fr)); gap: 9px; }
  .stat-card { gap: 10px; padding: 14px 12px; }
  .stat-icon { width: 34px; height: 34px; flex-basis: 34px; }
  .stat-icon svg { width: 18px; height: 18px; }
  .stat-num { font-size: 1.23rem; }
  .stat-label { font-size: .7rem; }
  .panel { padding: 16px 14px 12px; }
  .panel-code { font-size: .59rem; }
  .map-container, .map-empty { height: 250px; }
  .chart-wrapper, .chart-empty { height: 235px; }
  .charts-grid { grid-template-columns: 1fr; gap: 11px; }
  .loading-skeleton { grid-template-columns: repeat(2, minmax(0,1fr)); gap: 9px; }
  .skeleton-card { height: 78px; }
}
</style>
