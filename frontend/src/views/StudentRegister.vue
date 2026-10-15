<template>
  <div class="container py-5" style="max-width: 480px">
    <div class="card shadow-sm">
      <div class="card-body p-4">
        <h3 class="mb-4 text-center">Student Registration</h3>
        <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
        <form @submit.prevent="submit">
          <div class="mb-3">
            <label class="form-label">Full name</label>
            <input class="form-control" v-model.trim="form.full_name" required minlength="2" />
          </div>
          <div class="mb-3">
            <label class="form-label">Email</label>
            <input type="email" class="form-control" v-model.trim="form.email" required />
          </div>
          <div class="mb-3">
            <label class="form-label">Password (min 8 characters)</label>
            <input type="password" class="form-control" v-model="form.password" required minlength="8" />
          </div>
          <div class="mb-3">
            <label class="form-label">Confirm password</label>
            <input type="password" class="form-control" v-model="confirm" required />
          </div>
          <button class="btn btn-success w-100" :disabled="loading">Register</button>
        </form>
        <p class="text-center small mt-3 mb-0">Already registered? <router-link to="/login">Login</router-link></p>
      </div>
    </div>
  </div>
</template>

<script>
import api, { errMsg } from '@/api'
import { notify } from '@/store/toast'

export default {
  name: 'StudentRegister',
  data() {
    return { form: { full_name: '', email: '', password: '' }, confirm: '', error: '', loading: false }
  },
  methods: {
    async submit() {
      this.error = ''
      if (this.form.password !== this.confirm) {
        this.error = 'Passwords do not match'
        return
      }
      this.loading = true
      try {
        const res = await api.post('/api/auth/register/student', this.form)
        notify(res.data.message)
        this.$router.push('/login')
      } catch (err) {
        this.error = errMsg(err, 'Registration failed')
      } finally {
        this.loading = false
      }
    }
  }
}
</script>
