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
      name: 'chats',
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

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  const user = JSON.parse(localStorage.getItem('user') || 'null')
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if (to.meta.requiresAuth && !user?.is_staff && !user?.is_superuser) {
    // 非 staff / 非超级管理员无权访问后台
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    next('/login')
  } else if (to.meta.superadmin && !user?.is_superuser) {
    next('/')
  } else if (to.meta.guest && token) {
    next('/')
  } else {
    next()
  }
})

export default router
