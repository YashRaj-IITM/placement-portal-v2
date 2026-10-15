<template>
  <div class="container py-5" style="max-width: 520px">
    <div class="card shadow-sm">
      <div class="card-body p-4">
        <h3 class="mb-4 text-center">Company Registration</h3>
        <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
        <form @submit.prevent="submit">
          <div class="mb-3">
            <label class="form-label">Company name</label>
            <input class="form-control" v-model.trim="form.company_name" required minlength="2" />
          </div>
          <div class="mb-3">
            <label class="form-label">HR representative name</label>
            <input class="form-control" v-model.trim="form.full_name" required minlength="2" />
          </div>
          <div class="mb-3">
            <label class="form-label">HR contact (phone / email)</label>
            <input class="form-control" v-model.trim="form.hr_contact" />
          </div>
          <div class="mb-3">
            <label class="form-label">Website</label>
            <input type="url" class="form-control" v-model.trim="form.website" placeholder="https://..." />
          </div>
          <div class="mb-3">
            <label class="form-label">Login email</label>
            <input type="email" class="form-control" v-model.trim="form.email" required />
          </div>
          <div class="mb-3">
            <label class="form-label">Password (min 8 characters)</label>
            <input type="password" class="form-control" v-model="form.password" required minlength="8" />
          </div>
          <button class="btn btn-info w-100 text-white" :disabled="loading">Register</button>
        </form>
        <p class="text-center small mt-3 mb-0">Your account needs admin approval before you can post drives.</p>
      </div>
    </div>
  </div>
</template>

<script>
import api, { errMsg } from '@/api'
import { notify } from '@/store/toast'

export default {
  name: 'CompanyRegister',
  data() {
    return {
      form: { company_name: '', full_name: '', hr_contact: '', website: '', email: '', password: '' },
      error: '',
      loading: false
    }
  },
  methods: {
    async submit() {
      this.error = ''
      this.loading = true
      try {
        const res = await api.post('/api/auth/register/company', this.form)
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
