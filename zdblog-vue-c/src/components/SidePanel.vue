<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { fetchRandomArticles, fetchTags } from '@/api'

const router = useRouter()

const recommended = ref([])
const tags = ref([])
const sphereRef = ref(null)
const stageRef = ref(null)

const RADIUS = 100
let tagEls = []
let animationId = null
let rotationX = 0

function getContrastColor(hex) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  // W3C relative luminance
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return luminance > 0.55 ? '#1f2937' : '#fff'
}
let rotationY = 0
let autoRotate = true
let isDragging = false
let prevMouseX = 0
let prevMouseY = 0
let velocityX = 0
let velocityY = 0
let inertiaTimer = null

// Pre-computed positions on the sphere (normalized)
let spherePoints = []

function initSphere() {
  if (!stageRef.value || !tags.value.length) return
  stageRef.value.innerHTML = ''
  tagEls = []
  spherePoints = []

  const n = tags.value.length
  for (let i = 0; i < n; i++) {
    const phi = Math.acos(1 - 2 * (i + 0.5) / n)
    const theta = Math.PI * (1 + Math.sqrt(5)) * i
    spherePoints.push({
      x: Math.sin(phi) * Math.cos(theta),
      y: Math.sin(phi) * Math.sin(theta),
      z: Math.cos(phi),
      tag: tags.value[i],
    })

    const el = document.createElement('button')
    el.className = 'tag-bubble'
    el.textContent = tags.value[i].name
    const c = tags.value[i].color || '#3b82f6'
    el.style.setProperty('--tag-color', c)
    el.style.background = c
    el.style.color = getContrastColor(c)
    el.addEventListener('click', () => goTag(tags.value[i]))
    stageRef.value.appendChild(el)
    tagEls.push(el)
  }
}

function updatePositions() {
  const cosX = Math.cos(rotationX)
  const sinX = Math.sin(rotationX)
  const cosY = Math.cos(rotationY)
  const sinY = Math.sin(rotationY)
  const perspective = 600
  const cx = stageRef.value.clientWidth / 2
  const cy = stageRef.value.clientHeight / 2

  for (let i = 0; i < spherePoints.length; i++) {
    const sp = spherePoints[i]
    const el = tagEls[i]
    if (!el) continue

    // Scale to radius
    let x = sp.x * RADIUS
    let y = sp.y * RADIUS
    let z = sp.z * RADIUS

    // Rotate around Y axis
    let rx = x * cosY - z * sinY
    let rz = x * sinY + z * cosY
    // Rotate around X axis
    let ry = y * cosX - rz * sinX
    rz = y * sinX + rz * cosX

    const scale = perspective / (perspective + rz)
    const left = cx + rx * scale
    const top = cy + ry * scale
    const zIndex = Math.round(scale * 100)
    const opacity = 0.4 + scale * 0.6

    el.style.transform = `translate3d(${left - el.offsetWidth / 2}px, ${top - el.offsetHeight / 2}px, 0) scale(${scale})`
    el.style.zIndex = zIndex
    el.style.opacity = opacity
  }
}

function animate() {
  if (autoRotate) {
    rotationY += 0.003
  }
  updatePositions()
  animationId = requestAnimationFrame(animate)
}

function onMouseDown(e) {
  isDragging = true
  autoRotate = false
  prevMouseX = e.clientX
  prevMouseY = e.clientY
  clearTimeout(inertiaTimer)
}

function onMouseMove(e) {
  if (!isDragging) return
  const dx = e.clientX - prevMouseX
  const dy = e.clientY - prevMouseY
  velocityX = dy * 0.005
  velocityY = dx * 0.005
  rotationX += velocityX
  rotationY += velocityY
  prevMouseX = e.clientX
  prevMouseY = e.clientY
}

function onMouseUp() {
  isDragging = false
  inertiaTimer = setTimeout(() => {
    let vx = velocityX
    let vy = velocityY
    function decelerate() {
      vx *= 0.95
      vy *= 0.95
      if (Math.abs(vx) < 0.0005 && Math.abs(vy) < 0.0005) {
        autoRotate = true
        return
      }
      rotationX += vx
      rotationY += vy
      requestAnimationFrame(decelerate)
    }
    decelerate()
  }, 50)
}

function onWheel(e) {
  e.preventDefault()
  autoRotate = false
  clearTimeout(inertiaTimer)
  rotationY += e.deltaY * 0.005
  inertiaTimer = setTimeout(() => { autoRotate = true }, 1500)
}

function goTag(tag) {
  router.push({ path: '/articles', query: { search: tag.name } })
}

onMounted(async () => {
  try {
    const [recRes, tagRes] = await Promise.all([
      fetchRandomArticles().catch(() => []),
      fetchTags().catch(() => []),
    ])
    recommended.value = Array.isArray(recRes) ? recRes.slice(0, 3) : (recRes.results || []).slice(0, 3)
    tags.value = Array.isArray(tagRes) ? tagRes : (tagRes.results || [])
    if (tags.value.length) {
      // Wait for nextTick so stageRef is rendered
      await new Promise(r => setTimeout(r, 0))
      initSphere()
      animationId = requestAnimationFrame(animate)
    }
  } catch {
    // silent
  }
})

onUnmounted(() => {
  if (animationId) cancelAnimationFrame(animationId)
  clearTimeout(inertiaTimer)
})
</script>

<template>
  <aside class="side-panel">
    <div class="side-panel-inner">
      <!-- Recommended articles -->
      <div v-if="recommended.length" class="panel-section">
        <h4 class="panel-title">推荐文章</h4>
        <div class="rec-list">
          <router-link
            v-for="item in recommended"
            :key="item.id"
            :to="`/article/${item.id}`"
            class="rec-item"
          >
            <div v-if="item.cover" class="rec-cover" :style="{ backgroundImage: `url(${item.cover})` }"></div>
            <div class="rec-body">
              <span class="rec-title">{{ item.title }}</span>
              <span class="rec-meta">{{ item.view_count || 0 }} 阅读</span>
            </div>
          </router-link>
        </div>
      </div>

      <!-- Tag sphere -->
      <div v-if="tags.length" class="panel-section">
        <h4 class="panel-title">标签云</h4>
        <div
          ref="sphereRef"
          class="tag-sphere"
          @mousedown.prevent="onMouseDown"
          @mousemove="onMouseMove"
          @mouseup="onMouseUp"
          @mouseleave="onMouseUp"
          @wheel.prevent="onWheel"
        >
          <div ref="stageRef" class="sphere-stage"></div>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.side-panel {
  flex: 0 0 260px;
  width: 300px;
  position: sticky;
  top: 60px;           /* 距离视口顶部的距离，可调 */
  z-index: 100;     /* 确保不被其他元素覆盖 */
}

.side-panel-inner {
  position: sticky;
  top: calc(var(--navbar-height) + 20px);
}

.panel-section {
  height: 100%;
  background: var(--color-surface);
  border-radius: 12px;
  padding: 18px;
  margin-bottom: 16px;
  box-shadow: var(--shadow-card);
}

.panel-title {
  font-size: 0.88rem;
  font-weight: 700;
  margin-bottom: 14px;
  color: var(--color-text);
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border);
}

/* ---- Recommended ---- */
.rec-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rec-item {
  display: flex;
  gap: 10px;
  text-decoration: none;
  color: var(--color-text);
  border-radius: 8px;
  padding: 4px;
  transition: background 0.2s;
}
.rec-item:hover {
  background: var(--color-bg);
}

.rec-cover {
  width: 48px;
  height: 36px;
  border-radius: 4px;
  background-size: cover;
  background-position: center;
  flex-shrink: 0;
}

.rec-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.rec-title {
  font-size: 0.82rem;
  font-weight: 500;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rec-meta {
  font-size: 0.72rem;
  color: var(--color-text-secondary);
}

/* ---- Tag sphere ---- */
.tag-sphere {
  width: 100%;
  height: 260px;
  cursor: grab;
  user-select: none;
  -webkit-user-select: none;
  overflow: hidden;
}
.tag-sphere:active {
  cursor: grabbing;
}

.sphere-stage {
  position: relative;
  width: 100%;
  height: 90%;
}

:deep(.tag-bubble) {
  position: absolute;
  top: 0;
  left: 0;
  padding: 4px 10px;
  border-radius: 14px;
  font-size: 0.75rem;
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
  will-change: transform, opacity;
  box-shadow: 0 1px 4px rgba(0,0,0,0.12);
  border: none;
}
:deep(.tag-bubble:hover) {
  filter: brightness(1.1);
  box-shadow: 0 2px 8px rgba(0,0,0,0.22);
}
</style>
