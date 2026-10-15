<template>
  <div class="container py-5" style="max-width: 420px">
    <div class="card shadow-sm">
      <div class="card-body p-4">
        <h3 class="mb-4 text-center">Login</h3>
        <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
        <form @submit.prevent="submit">
          <div class="mb-3">
            <label class="form-label">Email</label>
            <input type="email" class="form-control" v-model.trim="email" required autofocus />
          </div>
          <div class="mb-3">
            <label class="form-label">Password</label>
            <input type="password" class="form-control" v-model="password" required />
          </div>
          <button class="btn btn-primary w-100" :disabled="loading">{{ loading ? 'Signing in...' : 'Login' }}</button>
        </form>
        <p class="text-center small mt-3 mb-0">
          New here? <router-link to="/register">Student</router-link> or
          <router-link to="/register-company">Company</router-link> registration
        </p>
      </div>
    </div>
  </div>
</template>

<script>
import { login } from '@/services/auth'
import { homeFor } from '@/store/session'
import { errMsg } from '@/api'

export default {
  name: 'UserLogin',
  data() {
    return { email: '', password: '', error: '', loading: false }
  },
  methods: {
    async submit() {
      this.error = ''
      this.loading = true
      try {
        const user = await login(this.email, this.password)
        this.$router.push(homeFor(user.role))
      } catch (err) {
        this.error = errMsg(err, 'Login failed')
      } finally {
        this.loading = false
      }
    }
  }
}
</script>
