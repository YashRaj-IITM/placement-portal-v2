import { createRouter, createWebHistory } from 'vue-router'
import { session, homeFor } from '@/store/session'
import Home from '@/views/Home.vue'
import Login from '@/views/Login.vue'
import StudentRegister from '@/views/StudentRegister.vue'
import CompanyRegister from '@/views/CompanyRegister.vue'
import StudentDashboard from '@/views/StudentDashboard.vue'
import CompanyDashboard from '@/views/CompanyDashboard.vue'
import AdminDashboard from '@/views/AdminDashboard.vue'

const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/login', name: 'Login', component: Login, meta: { guest: true } },
  { path: '/register', name: 'StudentRegister', component: StudentRegister, meta: { guest: true } },
  { path: '/register-company', name: 'CompanyRegister', component: CompanyRegister, meta: { guest: true } },
  { path: '/student', name: 'StudentDashboard', component: StudentDashboard, meta: { requiresAuth: true, role: 'student' } },
  { path: '/company', name: 'CompanyDashboard', component: CompanyDashboard, meta: { requiresAuth: true, role: 'company' } },
  { path: '/admin', name: 'AdminDashboard', component: AdminDashboard, meta: { requiresAuth: true, role: 'admin' } },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({ history: createWebHistory(), routes })

// The server enforces access; this guard only keeps the UI tidy.
router.beforeEach((to) => {
  const role = session.user ? session.user.role : null
  if (to.meta.requiresAuth && !session.token) return '/login'
  if (to.meta.role && to.meta.role !== role) return role ? homeFor(role) : '/login'
  if ((to.meta.guest || to.name === 'Home') && session.token) return homeFor(role)
})

export default router
