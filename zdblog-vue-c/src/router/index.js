import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
    },
    {
      path: '/articles',
      name: 'articles',
      component: () => import('@/views/ArticleListView.vue'),
    },
    {
      path: '/article/:id',
      name: 'article-detail',
      component: () => import('@/views/ArticleDetailView.vue'),
    },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('@/views/ChatView.vue'),
      meta: { requiresAuth: true, requireStaff: true },
    },
    {
      path: '/resources',
      name: 'resources',
      component: () => import('@/views/ResourceView.vue'),
    },
    {
      path: '/moments',
      name: 'moments',
      component: () => import('@/views/MomentsView.vue'),
    },
    {
      path: '/message-board',
      name: 'message-board',
      component: () => import('@/views/MessageBoardView.vue'),
    },
  ],
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0 }
  },
})

router.beforeEach(async (to, from, next) => {
  const token = localStorage.getItem('access_token')
  const user = JSON.parse(localStorage.getItem('user') || 'null')

  if (to.meta.requiresAuth && !token) {
    next('/')
    return
  }

  if (to.meta.requireStaff && !user?.is_superuser && !user?.is_staff) {
    const { ElMessage } = await import('element-plus')
    ElMessage.warning('当前功能属于体验功能，您可以联系站主后申请体验~')
    next('/')
    return
  }

  next()
})

export default router
