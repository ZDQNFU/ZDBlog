<script setup>
import { ref, onMounted } from 'vue'
import { fetchPublicConfig } from '@/api'

const runningDays = ref(0)
const hitokoto = ref(null)
const hitokotoLoading = ref(true)
const icpBeian = ref('')
const gonganBeian = ref('')

function getRunningDays() {
  const start = new Date('2026-06-01')
  const now = new Date()
  return Math.floor((now - start) / (1000 * 60 * 60 * 24))
}

async function fetchHitokoto() {
  try {
    const res = await fetch('https://v1.hitokoto.cn/?c=i&encode=json')
    const data = await res.json()
    hitokoto.value = data
  } catch {
    hitokoto.value = null
  } finally {
    hitokotoLoading.value = false
  }
}

async function fetchBeian() {
  try {
    const data = await fetchPublicConfig()
    icpBeian.value = data.ICP_BEIAN || ''
    gonganBeian.value = data.GONGAN_BEIAN || ''
  } catch {
    // 配置读取失败时保持为空，不影响页脚其余内容
    icpBeian.value = ''
    gonganBeian.value = ''
  }
}

onMounted(() => {
  runningDays.value = getRunningDays()
  fetchHitokoto()
  fetchBeian()
})
</script>

<template>
  <footer class="site-footer">
    <div class="footer-inner">
      <div class="footer-left">
        <p class="footer-powered">Proudly powered by <strong>ZDQNFU</strong></p>
        <div class="footer-running">
          <span class="rocket">&#128640;</span>
          <span>本站已运行 <strong>{{ runningDays }}</strong> 天</span>
        </div>
      </div>
      <div class="footer-right">
        <template v-if="hitokotoLoading">
          <p class="hitokoto-loading">诗词加载中...</p>
        </template>
        <template v-else-if="hitokoto">
          <p class="hitokoto-text">{{ hitokoto.hitokoto }}</p>
          <p class="hitokoto-from" v-if="hitokoto.from">
            —— {{ hitokoto.from_who ? hitokoto.from_who + ' ' : '' }}{{ hitokoto.from }}
          </p>
        </template>
      </div>
    </div>
    <div class="footer-inner" style="margin-top: 12px; justify-content: center;">
      <p>
        Copyright © 2025 ZDQNFU.
        <template v-if="icpBeian"> | <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">{{ icpBeian }}</a></template>
        <template v-if="gonganBeian"> | <a href="https://beian.mps.gov.cn/" target="_blank" rel="noopener noreferrer"><img src="/img/gongan-beian.png" class="beian-icon" alt="" />{{ gonganBeian }}</a></template>
      </p>
    </div>
  </footer>
</template>

<style scoped>
.site-footer {
  background: var(--footer-bg);
  backdrop-filter: saturate(180%) blur(10px);
  -webkit-backdrop-filter: saturate(180%) blur(10px);
  border-top: 1px solid var(--footer-border);
  padding: 28px 0;
  margin-top: auto;
}

.footer-inner {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 40px;
}

.footer-left {
  flex-shrink: 0;
}

.footer-powered {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
}

.footer-running {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.rocket {
  display: inline-block;
  animation: rocketBounce 1.2s ease-in-out infinite;
  font-size: 1rem;
}

.beian-icon {
  height: 18px;
  width: auto;
  vertical-align: -0.15em;
  margin-right: 4px;
}

@keyframes rocketBounce {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  25% { transform: translateY(-3px) rotate(-3deg); }
  75% { transform: translateY(-5px) rotate(3deg); }
}

.footer-right {
  flex: 1;
  min-width: 0;
  text-align: right;
}

.hitokoto-text {
  font-size: 0.9rem;
  color: var(--color-text);
  line-height: 1.6;
  font-style: italic;
}

.hitokoto-from {
  font-size: 0.78rem;
  color: var(--color-text-secondary);
  margin-top: 4px;
}

.hitokoto-loading {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

@media (max-width: 640px) {
  .footer-inner {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }
  .footer-right {
    text-align: center;
  }
}
</style>
