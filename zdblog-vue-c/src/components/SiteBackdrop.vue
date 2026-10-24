<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useTheme } from '@/composables/useTheme'

const { isDark } = useTheme()
const backgroundSource = computed(() => isDark.value
  ? '/img/hero-landscape-night.png'
  : '/img/hero-landscape-hd.png')

const snowCanvas = ref(null)
const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)')
let context, particles = [], frame = 0, lastTime = 0, width = 0, height = 0

function resize() {
  const canvas = snowCanvas.value
  if (!canvas || !context) return
  width = window.innerWidth
  height = window.innerHeight
  const ratio = Math.min(window.devicePixelRatio || 1, 2)
  canvas.width = Math.round(width * ratio)
  canvas.height = Math.round(height * ratio)
  context.setTransform(ratio, 0, 0, ratio, 0, 0)
  particles = Array.from({ length: width < 768 ? 32 : 76 }, () => ({
    x: Math.random() * width, y: Math.random() * height,
    radius: .9 + Math.random() * 2.6, speed: 13 + Math.random() * 24,
    phase: Math.random() * Math.PI * 2, opacity: .4 + Math.random() * .5,
  }))
  draw(0, 0)
}

function draw(delta, time) {
  context.clearRect(0, 0, width, height)
  for (const flake of particles) {
    flake.y += flake.speed * delta
    flake.x += Math.sin(time / 2400 + flake.phase) * 9 * delta
    if (flake.y > height + 5) { flake.y = -5; flake.x = Math.random() * width }
    if (flake.x < -5) flake.x = width + 5
    if (flake.x > width + 5) flake.x = -5
    context.beginPath()
    context.arc(flake.x, flake.y, flake.radius, 0, Math.PI * 2)
    context.fillStyle = `rgba(255,255,255,${flake.opacity})`
    context.fill()
  }
}

function animate(time) {
  frame = requestAnimationFrame(animate)
  if (time - lastTime < 1000 / 30) return
  const delta = lastTime ? Math.min((time - lastTime) / 1000, .08) : 0
  lastTime = time
  draw(delta, time)
}

function syncAnimation() {
  cancelAnimationFrame(frame)
  lastTime = 0
  if (!document.hidden && !motionPreference.matches) frame = requestAnimationFrame(animate)
  else if (context) draw(0, 0)
}

onMounted(() => {
  context = snowCanvas.value?.getContext('2d')
  if (!context) return
  resize()
  syncAnimation()
  window.addEventListener('resize', resize)
  document.addEventListener('visibilitychange', syncAnimation)
  motionPreference.addEventListener('change', syncAnimation)
})
onUnmounted(() => {
  cancelAnimationFrame(frame)
  window.removeEventListener('resize', resize)
  document.removeEventListener('visibilitychange', syncAnimation)
  motionPreference.removeEventListener('change', syncAnimation)
})
</script>

<template>
  <div class="site-backdrop" aria-hidden="true">
    <img :src="backgroundSource" alt="" fetchpriority="high" decoding="async" />
    <div class="backdrop-shade"></div>
    <canvas ref="snowCanvas" class="snow-canvas"></canvas>
  </div>
</template>

<style scoped>
.site-backdrop { position: fixed; inset: 0; z-index: -1; pointer-events: none; overflow: hidden; background: #4383ac; }
:global([data-theme="dark"]) .site-backdrop { background: #0a1426; }
.site-backdrop img { width: 100%; height: 100%; object-fit: cover; object-position: center; }
.backdrop-shade, .snow-canvas { position: absolute; inset: 0; width: 100%; height: 100%; }
.backdrop-shade { background: linear-gradient(90deg, #0d23314f, #0d23310a); transition: background .3s; }
:global([data-theme="dark"]) .backdrop-shade { background: rgba(9, 19, 32, .12); }
@media (max-width: 767px) { .site-backdrop img { object-position: 72% center; } }
</style>
