<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTheme } from '@/composables/useTheme'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const { isDark, toggle: toggleTheme } = useTheme()

const collapsed = ref(false)
const chatMenuExpanded = ref(false)
watch(
  () => route.path,
  (path) => {
    chatMenuExpanded.value = path.startsWith('/chats')
  },
  { immediate: true },
)
const sidebarWidth = computed(() => (collapsed.value ? '64px' : '200px'))

const baseMenuItems = [
  { path: '/', icon: 'DataAnalysis', label: '首页' },
  { path: '/articles', icon: 'Document', label: '文章管理' },
  { path: '/tags', icon: 'CollectionTag', label: '标签管理' },
  { path: '/categories', icon: 'Folder', label: '分类管理' },
  { path: '/comments', icon: 'ChatLineSquare', label: '评论管理' },
  { path: '/messages', icon: 'ChatLineRound', label: '留言管理' },
  { path: '/moments', icon: 'EditPen', label: '动态管理' },
  { path: '/links', icon: 'Link', label: '资源管理' },
  {
    path: '/chats',
    icon: 'ChatDotSquare',
    label: '聊天管理',
    children: [
      { path: '/chats/personas', label: '人物管理' },
      { path: '/chats/history', label: '聊天记录' },
    ],
  },
]

const menuItems = computed(() => {
  if (auth.user?.is_superuser) {
    return [
      ...baseMenuItems,
      { path: '/users', icon: 'User', label: '用户管理' },
      { path: '/tracking', icon: 'Monitor', label: '访问日志' },
      { path: '/settings', icon: 'Setting', label: '系统设置' },
    ]
  }
  return baseMenuItems
})

function isActive(path) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

function toggleSidebar() {
  collapsed.value = !collapsed.value
}

function handleLogout() {
  auth.logout()
}
</script>

<template>
  <div class="admin-layout">
    <!-- Sidebar -->
    <aside class="sidebar" :style="{ width: sidebarWidth }">
      <div class="sidebar-header">
        <span v-if="!collapsed" class="sidebar-logo">ZDBlog</span>
        <span v-else class="sidebar-logo-short">ZB</span>
      </div>
      <nav class="sidebar-nav">
        <div v-for="item in menuItems" :key="item.path" class="nav-group">
          <button
            v-if="item.children"
            class="nav-item nav-group-toggle"
            :class="{ active: isActive(item.path) }"
            :title="collapsed ? item.label : ''"
            :aria-expanded="!collapsed && chatMenuExpanded"
            @click="
              collapsed ? router.push('/chats/history') : (chatMenuExpanded = !chatMenuExpanded)
            "
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
            <el-icon v-if="!collapsed" class="submenu-chevron">
              <ArrowDown v-if="chatMenuExpanded" /><ArrowRight v-else />
            </el-icon>
          </button>
          <router-link
            v-else
            :to="item.path"
            :class="['nav-item', { active: isActive(item.path) }]"
            :title="collapsed ? item.label : ''"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
          </router-link>
          <div v-if="item.children && !collapsed && chatMenuExpanded" class="nav-submenu">
            <router-link
              v-for="child in item.children"
              :key="child.path"
              :to="child.path"
              class="nav-subitem"
              :class="{ active: route.path === child.path }"
            >
              <span class="submenu-dot"></span>{{ child.label }}
            </router-link>
          </div>
        </div>
      </nav>
    </aside>

    <!-- Right area: header + content -->
    <div class="main-area">
      <!-- Top header -->
      <header class="top-header">
        <div class="header-left">
          <button class="toggle-btn" @click="toggleSidebar">
            <el-icon :size="20"><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
          </button>
          <span class="header-title">管理后台</span>
        </div>
        <div class="header-right">
          <button
            class="theme-toggle-btn"
            @click="toggleTheme"
            :title="isDark ? '切换亮色模式' : '切换暗黑模式'"
          >
            <svg
              v-if="isDark"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <circle cx="12" cy="12" r="5" />
              <line x1="12" y1="1" x2="12" y2="3" />
              <line x1="12" y1="21" x2="12" y2="23" />
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
              <line x1="1" y1="12" x2="3" y2="12" />
              <line x1="21" y1="12" x2="23" y2="12" />
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
            </svg>
            <svg
              v-else
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            </svg>
          </button>
          <span class="header-user">{{ auth.user?.username }}</span>
          <button class="logout-btn" @click="handleLogout">
            <el-icon><SwitchButton /></el-icon>
            <span>退出登录</span>
          </button>
        </div>
      </header>

      <!-- Main content -->
      <main class="main-content">
        <slot />
      </main>
    </div>
  </div>
</template>

<style scoped>
.admin-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* ---- Sidebar ---- */
.sidebar {
  background: #1d1e2c;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  color: #ccc;
  transition: width 0.25s ease;
  overflow: hidden;
}

.sidebar-header {
  padding: 20px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  text-align: center;
  white-space: nowrap;
}
.sidebar-logo {
  font-size: 1.25rem;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.03em;
}
.sidebar-logo-short {
  font-size: 1.1rem;
  font-weight: 700;
  color: #60a5fa;
}

.sidebar-nav {
  flex: 1;
  padding: 8px 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  font-size: 0.9rem;
  color: #aaa;
  transition:
    background 0.15s,
    color 0.15s;
  cursor: pointer;
  white-space: nowrap;
  text-decoration: none;
}
.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #ddd;
}
.nav-item.active {
  background: var(--color-primary);
  color: #fff;
}
.nav-label {
  overflow: hidden;
}
.nav-group-toggle {
  width: 100%;
  border: 0;
  background: transparent;
  text-align: left;
}
.submenu-chevron {
  margin-left: auto;
  font-size: 12px;
}
.nav-submenu {
  padding: 2px 0 6px 20px;
  background: rgba(0, 0, 0, 0.12);
}
.nav-subitem {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 5px;
  color: #aaa;
  font-size: 0.84rem;
  text-decoration: none;
  white-space: nowrap;
}
.nav-subitem:hover,
.nav-subitem.active {
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
}
.submenu-dot {
  width: 5px;
  height: 5px;
  flex: 0 0 5px;
  border-radius: 50%;
  background: currentColor;
}

/* ---- Main area ---- */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* ---- Top header ---- */
.top-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 52px;
  padding: 0 20px;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background 0.15s;
}
.toggle-btn:hover {
  background: var(--color-bg);
}

.header-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-text);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-user {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 0.85rem;
  cursor: pointer;
  transition:
    color 0.15s,
    border-color 0.15s,
    background 0.15s;
}
.logout-btn:hover {
  color: #f56c6c;
  border-color: #f56c6c;
  background: #fef0f0;
}

.theme-toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition:
    background 0.15s,
    color 0.15s,
    border-color 0.15s;
  flex-shrink: 0;
}
.theme-toggle-btn:hover {
  background: var(--color-bg);
  color: var(--color-primary);
  border-color: var(--color-primary);
}

/* ---- Main content ---- */
.main-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 24px;
  background: var(--color-bg);
}

@media (max-width: 768px) {
  .sidebar {
    width: 64px !important;
  }
  .nav-item {
    justify-content: center;
    padding: 12px 0;
  }
  .sidebar-header {
    padding: 16px 0;
  }
  .sidebar-logo-short {
    display: block;
  }
  .toggle-btn {
    display: none;
  }
  .top-header {
    padding: 0 12px;
  }
  .main-content {
    padding: 16px;
  }
}

@media (max-width: 480px) {
  .header-user {
    display: none;
  }
}
</style>
