<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTheme } from '@/composables/useTheme'
import AuthModal from '@/components/AuthModal.vue'
import SiteFooter from '@/components/SiteFooter.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const { isDark, toggle: toggleTheme } = useTheme()
const showAuthModal = ref(false)

const scrolled = ref(false)
const showBackTop = ref(false)
const showChatTip = ref(false)
const mobileMenuOpen = ref(false)

const isChatPage = computed(() => route.path === '/chat')

const navItems = [
  { to: '/', label: '首页' },
  { to: '/articles', label: '文章' },
  { to: '/resources', label: '资源' },
  { to: '/message-board', label: '留言板' },
  { type: 'chat', label: '聊天' },
]

function onScroll() {
  const y = window.scrollY
  scrolled.value = y > 60
  showBackTop.value = y > 500
}

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function handleLogout() {
  auth.logout()
  mobileMenuOpen.value = false
}

function handleChatClick() {
  const user = auth.user
  if (!auth.isAuthenticated || (!user?.is_superuser && !user?.is_staff)) {
    showChatTip.value = true
    setTimeout(() => { showChatTip.value = false }, 3000)
    return
  }
  mobileMenuOpen.value = false
  router.push('/chat')
}

function closeMobileMenu() {
  mobileMenuOpen.value = false
}

function isActive(to) {
  if (to === '/') return route.path === '/'
  return route.path.startsWith(to)
}

onMounted(() => {
  window.addEventListener('scroll', onScroll, { passive: true })
  if (auth.isAuthenticated) {
    auth.refreshUser()
  }
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
})
</script>

<template>
  <div class="app-shell">
    <header v-if="!isChatPage" :class="['navbar', { 'navbar-scrolled': scrolled }]">
      <button class="hamburger-btn" @click="mobileMenuOpen = !mobileMenuOpen" aria-label="菜单">
        <span></span><span></span><span></span>
      </button>

      <router-link to="/" class="logo">ZDBlog</router-link>

      <nav class="nav-links desktop-nav">
        <router-link to="/" class="nav-link">
          <svg width="16" height="16" viewBox="0 0 24 24"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" fill="#409eff" stroke="#409eff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><polyline points="9 22 9 12 15 12 15 22" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          首页
        </router-link>
        <router-link to="/articles" class="nav-link">
          <svg width="16" height="16" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" fill="#67c23a" stroke="#67c23a" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><polyline points="14 2 14 8 20 8" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><line x1="16" y1="13" x2="8" y2="13" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"/><line x1="16" y1="17" x2="8" y2="17" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg>
          文章
        </router-link>
        <router-link to="/resources" class="nav-link">
          <svg width="16" height="16" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="#e6a23c" stroke="#e6a23c" stroke-width="1.5"/><path d="M8 12h8M12 8v8" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/></svg>
          资源
        </router-link>
        <router-link to="/message-board" class="nav-link">
          <svg width="16" height="16" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="3" fill="#f97316" stroke="#f97316" stroke-width="1.5"/><line x1="8" y1="8" x2="16" y2="8" stroke="#fff" stroke-width="2" stroke-linecap="round"/><line x1="8" y1="12" x2="16" y2="12" stroke="#fff" stroke-width="2" stroke-linecap="round"/><line x1="8" y1="16" x2="12" y2="16" stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg>
          留言板
        </router-link>
        <a class="nav-link" @click.prevent="handleChatClick" href="#">
          <svg width="16" height="16" viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" fill="#8b5cf6" stroke="#8b5cf6" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="9" cy="10" r="1.5" fill="#fff"/><circle cx="15" cy="10" r="1.5" fill="#fff"/></svg>
          聊天
        </a>
      </nav>

      <div class="nav-actions">
        <button class="theme-toggle-btn" @click="toggleTheme" :title="isDark ? '切换亮色模式' : '切换暗黑模式'">
          <svg v-if="isDark" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="5"/>
            <line x1="12" y1="1" x2="12" y2="3"/>
            <line x1="12" y1="21" x2="12" y2="23"/>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
            <line x1="1" y1="12" x2="3" y2="12"/>
            <line x1="21" y1="12" x2="23" y2="12"/>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
          </svg>
          <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
          </svg>
        </button>
        <template v-if="auth.isAuthenticated">
          <span class="nav-user">{{ auth.user?.username }}</span>
          <button class="nav-auth-btn" @click="handleLogout">登出</button>
        </template>
        <button v-else class="nav-auth-btn" @click="showAuthModal = true">登录</button>
      </div>
    </header>

    <!-- Mobile overlay -->
    <Transition name="overlay-fade">
      <div v-if="mobileMenuOpen" class="mobile-overlay" @click="closeMobileMenu"></div>
    </Transition>

    <!-- Mobile sidebar (manual class toggle for reliability) -->
    <aside :class="['mobile-sidebar', { 'sidebar-open': mobileMenuOpen }]">
      <div class="mobile-sidebar-header">
        <span class="sidebar-logo">ZDBlog</span>
      </div>
      <nav class="mobile-nav">
        <router-link
          v-for="item in navItems.filter(i => i.type !== 'chat')"
          :key="item.label"
          :to="item.to"
          :class="['mobile-nav-item', { active: isActive(item.to) }]"
          @click="closeMobileMenu"
        >
          <svg v-if="item.to === '/'" width="20" height="20" viewBox="0 0 24 24"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" fill="#409eff" stroke="#409eff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><polyline points="9 22 9 12 15 12 15 22" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          <svg v-else-if="item.to === '/articles'" width="20" height="20" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" fill="#67c23a" stroke="#67c23a" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><polyline points="14 2 14 8 20 8" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><line x1="16" y1="13" x2="8" y2="13" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"/><line x1="16" y1="17" x2="8" y2="17" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg>
          <svg v-else-if="item.to === '/resources'" width="20" height="20" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="#e6a23c" stroke="#e6a23c" stroke-width="1.5"/><path d="M8 12h8M12 8v8" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/></svg>
          <svg v-else-if="item.to === '/message-board'" width="20" height="20" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="3" fill="#f97316" stroke="#f97316" stroke-width="1.5"/><line x1="8" y1="8" x2="16" y2="8" stroke="#fff" stroke-width="2" stroke-linecap="round"/><line x1="8" y1="12" x2="16" y2="12" stroke="#fff" stroke-width="2" stroke-linecap="round"/><line x1="8" y1="16" x2="12" y2="16" stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg>
          {{ item.label }}
        </router-link>
        <a
          class="mobile-nav-item"
          @click.prevent="handleChatClick"
          href="#"
        >
          <svg width="20" height="20" viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" fill="#8b5cf6" stroke="#8b5cf6" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="9" cy="10" r="1.5" fill="#fff"/><circle cx="15" cy="10" r="1.5" fill="#fff"/></svg>
          聊天
        </a>
      </nav>
    </aside>

    <div :class="{ 'app-content': !isChatPage }">
      <router-view v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </router-view>

      <SiteFooter v-if="!isChatPage" />
    </div>

    <Transition name="back-top-fade">
      <button v-show="showBackTop" class="back-top-btn" @click="scrollToTop" title="回到顶部">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"/></svg>
      </button>
    </Transition>

    <AuthModal v-if="showAuthModal" @close="showAuthModal = false" />

    <Transition name="chat-tip-fade">
      <div v-if="showChatTip" class="chat-tip-card">
        <div class="chat-tip-icon">&#128172;</div>
        <p>此功能需要向站主申请后才能使用哦~</p>
      </div>
    </Transition>
  </div>
</template>

<style>
@import '@/assets/main.css';
</style>

<!-- Mobile sidebar & overlay styles (unscoped for Transition compatibility) -->
<style>
.mobile-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.35);
}

.overlay-fade-enter-active,
.overlay-fade-leave-active { transition: opacity 0.25s; }
.overlay-fade-enter-from,
.overlay-fade-leave-to { opacity: 0; }

.mobile-sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 240px;
  z-index: 1001;
  background: #1d1e2c;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  transform: translateX(-100%);
  transition: transform 0.25s ease;
}
.mobile-sidebar.sidebar-open {
  transform: translateX(0);
}

.mobile-sidebar-header {
  padding: 20px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  text-align: center;
}
.sidebar-logo {
  font-size: 1.2rem;
  font-weight: 700;
  color: #fff;
}

.mobile-nav {
  flex: 1;
  padding: 8px 0;
}

.mobile-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 24px;
  font-size: 0.95rem;
  color: #aaa;
  text-decoration: none;
  transition: background 0.15s, color 0.15s;
}
.mobile-nav-item:hover,
.mobile-nav-item.active {
  background: rgba(255,255,255,0.06);
  color: #60a5fa;
}
</style>

<style scoped>
/* ---------- Navbar (glass morphism) ---------- */
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 999;
  height: var(--navbar-height);
  display: flex;
  align-items: center;
  background: var(--navbar-bg);
  backdrop-filter: saturate(180%) blur(10px);
  -webkit-backdrop-filter: saturate(180%) blur(10px);
  border-bottom: 1px solid rgba(59, 130, 246, 0.12);
  transition: background 0.35s, box-shadow 0.35s, backdrop-filter 0.35s, border-color 0.35s;
}

.navbar-scrolled {
  background: var(--navbar-bg-scrolled);
  backdrop-filter: saturate(180%) blur(14px);
  -webkit-backdrop-filter: saturate(180%) blur(14px);
  box-shadow: 0 1px 8px rgba(59, 130, 246, 0.08);
  border-bottom-color: rgba(59, 130, 246, 0.2);
}

.logo {
  margin-left: 100px;
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--color-primary);
  transition: color 0.35s;
  flex-shrink: 0;
}

.nav-links {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 24px;
}

/* ---------- Hamburger button ---------- */
.hamburger-btn {
  display: none;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  width: 34px;
  height: 34px;
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 6px;
  margin-left: 12px;
  flex-shrink: 0;
}
.hamburger-btn span {
  display: block;
  width: 100%;
  height: 2px;
  background: var(--color-text);
  border-radius: 2px;
  transition: transform 0.25s, opacity 0.25s;
}

.nav-link {
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--color-text);
  padding: 4px 0;
  border-bottom: 2px solid transparent;
  transition: color 0.2s, border-color 0.25s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.nav-link:hover,
.nav-link.router-link-exact-active {
  border-bottom-color: var(--color-primary);
  color: var(--color-primary);
}

/* ---------- Theme toggle ---------- */
.theme-toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background 0.2s, color 0.2s, border-color 0.2s;
  flex-shrink: 0;
}
.theme-toggle-btn:hover {
  background: var(--color-bg);
  color: var(--color-primary);
  border-color: var(--color-primary);
}

/* ---------- Nav actions (auth) ---------- */
.nav-actions {
  margin-left: auto;
  margin-right: 100px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.nav-user {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-text);
}

.nav-auth-btn {
  padding: 6px 18px;
  border: 1px solid var(--color-primary);
  border-radius: 8px;
  background: transparent;
  color: var(--color-primary);
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}
.nav-auth-btn:hover {
  background: var(--color-primary);
  color: #fff;
}

/* ---------- Page transitions ---------- */
.page-enter-active,
.page-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* ---------- Back to top ---------- */
.back-top-btn {
  position: fixed;
  bottom: 28px;
  right: 28px;
  z-index: 900;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  border: none;
  background: var(--back-top-bg);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  box-shadow: 0 2px 10px rgba(0,0,0,0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--color-text-secondary);
  transition: transform 0.2s, box-shadow 0.2s, color 0.2s;
}
.back-top-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.16);
  color: var(--color-primary);
}

/* ---------- App content wrapper (pushes footer down) ---------- */
.app-content {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* ---------- Chat tip card ---------- */
.chat-tip-card {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 2000;
  background: var(--chat-tip-bg);
  border-radius: 16px;
  padding: 36px 40px;
  text-align: center;
  box-shadow: 0 12px 40px rgba(0,0,0,0.15);
  max-width: 360px;
}

.chat-tip-icon {
  font-size: 2.6rem;
  margin-bottom: 12px;
}

.chat-tip-card p {
  font-size: 0.95rem;
  color: var(--color-text);
  line-height: 1.6;
}

.chat-tip-fade-enter-active { transition: opacity 0.3s, transform 0.3s; }
.chat-tip-fade-leave-active { transition: opacity 0.25s, transform 0.25s; }
.chat-tip-fade-enter-from,
.chat-tip-fade-leave-to {
  opacity: 0;
  transform: translate(-50%, -50%) scale(0.9);
}

.back-top-fade-enter-active {
  transition: opacity 0.28s, transform 0.28s;
}
.back-top-fade-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}
.back-top-fade-enter-from,
.back-top-fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

/* ---------- Responsive ---------- */
@media (max-width: 860px) {
  .desktop-nav { display: none; }
  .hamburger-btn { display: flex; }
  .logo { margin-left: 0; }
  .nav-actions { margin-right: 12px; }
}

@media (max-width: 480px) {
  .nav-user { display: none; }
}
</style>
