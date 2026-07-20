import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/monitor',
    },
    {
      path: '/rules',
      name: 'rules',
      component: () => import('@/pages/RulesPage.vue'),
    },
    {
      path: '/monitor',
      name: 'monitor',
      component: () => import('@/pages/MonitorPage.vue'),
    },
    {
      path: '/window',
      name: 'window',
      component: () => import('@/pages/WindowPage.vue'),
    },
    {
      path: '/logs',
      name: 'logs',
      component: () => import('@/pages/LogsPage.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/pages/NotFoundPage.vue'),
    },
  ],
})

export default router
