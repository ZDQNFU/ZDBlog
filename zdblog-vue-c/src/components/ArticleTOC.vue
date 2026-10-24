<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  toc: { type: Array, default: () => [] },
})

const activeId = ref('')
let observer = null

function scrollToHeading(id) {
  const el = document.getElementById(id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    activeId.value = id
  }
}

function setupObserver() {
  if (observer) observer.disconnect()
  const headingEls = props.toc
    .map(t => document.getElementById(t.id))
    .filter(Boolean)

  if (headingEls.length === 0) return

  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          activeId.value = entry.target.id
          break
        }
      }
    },
    { rootMargin: '-80px 0px -60% 0px', threshold: 0 }
  )

  headingEls.forEach(el => observer.observe(el))
}

watch(() => props.toc, () => {
  // wait for DOM update then re-observe
  setTimeout(setupObserver, 100)
}, { deep: true })

onMounted(() => { setTimeout(setupObserver, 200) })
onUnmounted(() => { if (observer) observer.disconnect() })
</script>

<template>
  <nav v-if="toc.length" class="toc-nav">
    <h4 class="toc-title">目录</h4>
    <ul class="toc-list">
      <li
        v-for="item in toc"
        :key="item.id"
        :class="['toc-item', `toc-level-${item.level}`, { active: activeId === item.id }]"
      >
        <a :href="`#${item.id}`" @click.prevent="scrollToHeading(item.id)">{{ item.text }}</a>
      </li>
    </ul>
  </nav>
</template>

<style scoped>
.toc-nav {
  width: 200px;
  flex-shrink: 0;
  position: sticky;
  top: calc(var(--navbar-height) + 32px);
  align-self: flex-start;
  max-height: calc(100vh - var(--navbar-height) - 64px);
  overflow-y: auto;
  padding: 22px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: var(--color-surface);
}

.toc-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.toc-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.toc-item {
  margin-bottom: 4px;
  line-height: 1.45;
}

.toc-item a {
  display: block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: color 0.15s, background 0.15s;
  border-left: 2px solid transparent;
}

.toc-item a:hover {
  color: var(--color-primary);
  background: rgba(59, 130, 246, 0.06);
}

.toc-item.active a {
  color: var(--color-primary);
  background: rgba(59, 130, 246, 0.08);
  border-left-color: var(--color-primary);
}

.toc-level-1 a { padding-left: 8px; font-weight: 600; }
.toc-level-2 a { padding-left: 20px; }
.toc-level-3 a { padding-left: 32px; font-size: 0.8rem; }

@media (max-width: 1024px) {
  .toc-nav { display: none; }
}
</style>
