<template>
  <div class="container py-4">
    <h2 class="mb-3">Student Dashboard</h2>
    <ul class="nav nav-tabs mb-4">
      <li class="nav-item" v-for="t in tabs" :key="t.key">
        <a class="nav-link" :class="{ active: tab === t.key }" href="#" @click.prevent="tab = t.key">{{ t.label }}</a>
      </li>
    </ul>

    <!-- Profile -->
    <div v-if="tab === 'profile'" class="card shadow-sm p-4" style="max-width: 600px">
      <h5 class="mb-3">My Profile <small class="text-muted">({{ profile.email }})</small></h5>
      <form @submit.prevent="saveProfile">
        <div class="mb-3"><label class="form-label">Full name</label>
          <input class="form-control" v-model="form.full_name" required minlength="2" /></div>
        <div class="mb-3"><label class="form-label">Branch</label>
          <input class="form-control" v-model="form.branch" placeholder="e.g. CSE" /></div>
        <div class="row">
          <div class="col mb-3"><label class="form-label">CGPA (0-10)</label>
            <input type="number" step="0.01" min="0" max="10" class="form-control" v-model="form.cgpa" /></div>
          <div class="col mb-3"><label class="form-label">Graduation year</label>
            <input type="number" min="2000" max="2100" class="form-control" v-model="form.graduation_year" /></div>
        </div>
        <div class="mb-3"><label class="form-label">Resume link</label>
          <input type="url" class="form-control" v-model="form.resume_path" placeholder="https://..." /></div>
        <button class="btn btn-primary me-2">Save profile</button>
        <button type="button" class="btn btn-outline-danger" @click="deleteAccount">Delete my account</button>
      </form>
    </div>

    <!-- Drives -->
    <div v-if="tab === 'drives'">
      <div class="d-flex flex-wrap align-items-center mb-3 gap-3">
        <input class="form-control" style="max-width: 360px" v-model="query" placeholder="Search job title or company..." />
        <div class="form-check">
          <input class="form-check-input" type="checkbox" id="elig" v-model="onlyEligible" />
          <label class="form-check-label" for="elig">Only drives I'm eligible for</label>
        </div>
      </div>
      <div class="row">
        <div class="col-md-4 mb-4" v-for="d in drives" :key="d.id">
          <div class="card shadow-sm h-100">
            <div class="card-body d-flex flex-column">
              <h5 class="text-primary">{{ d.job_title }}</h5>
              <h6 class="text-muted">{{ d.company_name }}</h6>
              <p class="small flex-grow-1">{{ d.job_description.length > 120 ? d.job_description.slice(0, 120) + '...' : d.job_description }}</p>
              <p class="small mb-1"><strong>Eligibility:</strong> {{ d.eligible_branches || 'Any branch' }} |
                CGPA {{ d.min_cgpa }}+ | {{ d.eligible_years || 'Any year' }}</p>
              <p class="small text-danger"><strong>Deadline:</strong> {{ fmtDate(d.deadline) }}</p>
              <button v-if="d.applied" class="btn btn-secondary w-100" disabled>Already applied</button>
              <template v-else>
                <button class="btn btn-success w-100" :disabled="!d.eligible" @click="apply(d)">Apply now</button>
                <div v-if="!d.eligible" class="small text-danger mt-1">{{ d.ineligible_reason }}</div>
              </template>
            </div>
          </div>
        </div>
        <p v-if="!drives.length" class="text-center text-muted mt-4">No open drives match your search.</p>
      </div>
    </div>

    <!-- Applications -->
    <div v-if="tab === 'applications'">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="mb-0">My Applications</h5>
        <button class="btn btn-outline-success" :disabled="exporting" @click="exportCsv">
          {{ exporting ? 'Preparing CSV...' : 'Export to CSV' }}
        </button>
      </div>
      <table class="table table-hover bg-white shadow-sm">
        <thead class="table-light"><tr><th>Company</th><th>Job</th><th>Applied on</th><th>Status</th><th></th></tr></thead>
        <tbody>
          <tr v-for="a in applications" :key="a.application_id">
            <td>{{ a.company_name }}</td><td>{{ a.job_title }}</td><td>{{ fmtDate(a.application_date) }}</td>
            <td><span class="badge" :class="badge(a.status)">{{ a.status }}</span></td>
            <td class="text-end">
              <button v-if="a.status === 'Applied'" class="btn btn-sm btn-outline-danger" @click="withdraw(a)">Withdraw</button>
            </td>
          </tr>
          <tr v-if="!applications.length"><td colspan="5" class="text-center text-muted">You haven't applied to any drive yet.</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import api, { errMsg } from '@/api'
import { notify } from '@/store/toast'
import { clearSession } from '@/store/session'
import { fmtDate, badge } from '@/utils'

export default {
  name: 'StudentDashboard',
  data() {
    return {
      tab: 'profile',
      tabs: [
        { key: 'profile', label: 'My Profile' },
        { key: 'drives', label: 'Browse Drives' },
        { key: 'applications', label: 'My Applications' }
      ],
      profile: {}, form: {}, drives: [], applications: [],
      query: '', onlyEligible: false, exporting: false, timer: null
    }
  },
  watch: {
    tab() { this.load() },
    onlyEligible() { this.loadDrives() },
    query() {
      clearTimeout(this.timer)
      this.timer = setTimeout(this.loadDrives, 300)
    }
  },
  mounted() { this.load() },
  methods: {
    fmtDate, badge,
    async load() {
      try {
        if (this.tab === 'profile') await this.loadProfile()
        else if (this.tab === 'drives') await this.loadDrives()
        else await this.loadApplications()
      } catch (err) { notify(errMsg(err), 'error') }
    },
    async loadProfile() {
      const res = await api.get('/api/student/profile')
      this.profile = res.data
      this.form = { ...res.data }
    },
    async loadDrives() {
      const res = await api.get('/api/student/drives', { params: { q: this.query, eligible: this.onlyEligible } })
      this.drives = res.data
    },
    async loadApplications() {
      this.applications = (await api.get('/api/student/applications')).data
    },
    async saveProfile() {
      try {
        const { full_name, branch, cgpa, graduation_year, resume_path } = this.form
        await api.put('/api/student/profile', { full_name, branch, cgpa, graduation_year, resume_path })
        notify('Profile updated')
        this.loadProfile()
      } catch (err) { notify(errMsg(err, 'Could not update profile'), 'error') }
    },
    async deleteAccount() {
      if (!confirm('Delete your account and all your applications? This cannot be undone.')) return
      try {
        await api.delete('/api/student/account')
        clearSession()
        this.$router.push('/login')
      } catch (err) { notify(errMsg(err), 'error') }
    },
    async apply(drive) {
      if (!confirm(`Apply for ${drive.job_title} at ${drive.company_name}?`)) return
      try {
        await api.post(`/api/student/drives/${drive.id}/apply`)
        notify('Application submitted')
        this.tab = 'applications'
      } catch (err) { notify(errMsg(err, 'Application failed'), 'error') }
    },
    async withdraw(app) {
      if (!confirm('Withdraw this application?')) return
      try {
        await api.delete(`/api/student/applications/${app.application_id}`)
        notify('Application withdrawn')
        this.loadApplications()
      } catch (err) { notify(errMsg(err), 'error') }
    },
    async exportCsv() {
      this.exporting = true
      try {
        const start = await api.post('/api/student/export')
        const taskId = start.data.task_id
        for (let i = 0; i < 30; i++) {
          await new Promise((r) => setTimeout(r, 1500))
          const res = await api.get(`/api/student/export/${taskId}`, { responseType: 'blob' })
          if (res.status === 200) {
            const url = URL.createObjectURL(res.data)
            const link = document.createElement('a')
            link.href = url
            link.download = 'applications.csv'
            link.click()
            URL.revokeObjectURL(url)
            notify('CSV downloaded (a copy was also emailed to you)')
            return
          }
        }
        notify('Export is taking longer than expected, try again shortly', 'error')
      } catch (err) {
        notify(errMsg(err, 'Export failed. Is the Celery worker running?'), 'error')
      } finally { this.exporting = false }
    }
  }
}
</script>
