import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { guest: true, layout: 'blank' },
    },
    {
      path: '/',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { requiresAuth: true, layout: 'admin' },
    },
    {
      path: '/articles',
      name: 'articles',
      component: () => import('@/views/ArticleManageView.vue'),
      meta: { requiresAuth: true, layout: 'admin' },
    },
    {
      path: '/articles/edit/:id?',
      name: 'article-edit',
      component: () => import('@/views/ArticleEditView.vue'),
      meta: { requiresAuth: true, layout: 'blank' },
    },
    {
      path: '/tags',
      name: 'tags',
      component: () => import('@/views/TagManageView.vue'),
      meta: { requiresAuth: true, layout: 'admin' },
    },
    {
      path: '/categories',
      name: 'categories',
      component: () => import('@/views/CategoryManageView.vue'),
      meta: { requiresAuth: true, layout: 'admin' },
    },
    {
      path: '/comments',
      name: 'comments',
      component: () => import('@/views/CommentManageView.vue'),
      meta: { requiresAuth: true, layout: 'admin' },
    },
    {
      path: '/users',
      name: 'users',
      component: () => import('@/views/UserManageView.vue'),
      meta: { requiresAuth: true, layout: 'admin', superadmin: true },
    },
    {
      path: '/links',
      name: 'links',
      component: () => import('@/views/ResourceManageView.vue'),
      meta: { requiresAuth: true, layout: 'admin' },
    },
    {
      path: '/chats',
      redirect: '/chats/history',
    },
    {
      path: '/chats/personas',
      name: 'chat-personas',
      component: () => import('@/views/ChatPersonaManageView.vue'),
      meta: { requiresAuth: true, layout: 'admin' },
    },
    {
      path: '/chats/history',
      name: 'chat-history',
      component: () => import('@/views/ChatManageView.vue'),
      meta: { requiresAuth: true, layout: 'admin' },
    },
    {
      path: '/tracking',
      name: 'tracking',
      component: () => import('@/views/TrackingManageView.vue'),
      meta: { requiresAuth: true, layout: 'admin' },
    },
    {
      path: '/messages',
      name: 'messages',
      component: () => import('@/views/MessageManageView.vue'),
      meta: { requiresAuth: true, layout: 'admin' },
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/SystemConfigView.vue'),
      meta: { requiresAuth: true, layout: 'admin', superadmin: true },
    },
  ],
})

// vue-router 5 起改用返回值：返回 false/路由地址即拦截，返回 undefined 表示放行
router.beforeEach((to) => {
  const token = localStorage.getItem('access_token')
  const user = JSON.parse(localStorage.getItem('user') || 'null')
  if (to.meta.requiresAuth && !token) {
    return '/login'
  }
  if (to.meta.requiresAuth && !user?.is_staff && !user?.is_superuser) {
    // 非 staff / 非超级管理员无权访问后台
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    return '/login'
  }
  if (to.meta.superadmin && !user?.is_superuser) {
    return '/'
  }
  if (to.meta.guest && token) {
    return '/'
  }
})

export default router
