<template>
  <div class="d-flex flex-column min-vh-100 bg-light">
    <nav class="navbar navbar-dark bg-primary shadow-sm">
      <div class="container">
        <router-link class="navbar-brand fw-bold" to="/">Placement Portal</router-link>
        <div class="d-flex align-items-center text-white">
          <template v-if="session.token">
            <span class="me-3 small">{{ session.user && session.user.full_name }}
              <span class="badge bg-light text-primary ms-1">{{ session.user && session.user.role }}</span>
            </span>
            <button class="btn btn-sm btn-outline-light" @click="doLogout">Logout</button>
          </template>
          <template v-else>
            <router-link class="btn btn-sm btn-outline-light me-2" to="/login">Login</router-link>
            <router-link class="btn btn-sm btn-light" to="/register">Register</router-link>
          </template>
        </div>
      </div>
    </nav>

    <div v-if="toast.message" class="alert position-fixed top-0 start-50 translate-middle-x mt-5 shadow"
         :class="toast.type === 'error' ? 'alert-danger' : 'alert-success'" style="z-index: 2000">
      {{ toast.message }}
    </div>

    <main class="flex-grow-1"><router-view /></main>
  </div>
</template>

<script>
import { session } from '@/store/session'
import { toast } from '@/store/toast'
import { logout } from '@/services/auth'

export default {
  name: 'App',
  data() {
    return { session, toast }
  },
  methods: {
    async doLogout() {
      await logout()
      this.$router.push('/login')
    }
  }
}
</script>
