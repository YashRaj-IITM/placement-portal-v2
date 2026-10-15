<template>
  <div class="container py-4">
    <h2 class="mb-3">Admin Dashboard</h2>
    <ul class="nav nav-tabs mb-4">
      <li class="nav-item" v-for="t in tabs" :key="t.key">
        <a class="nav-link" :class="{ active: tab === t.key }" href="#" @click.prevent="tab = t.key">{{ t.label }}</a>
      </li>
    </ul>

    <div v-if="tab !== 'overview'" class="mb-3" style="max-width: 360px">
      <input class="form-control" v-model="query" placeholder="Search..." />
    </div>

    <!-- Overview -->
    <div v-if="tab === 'overview'">
      <div class="row">
        <div class="col-md-3 mb-3" v-for="c in cards" :key="c.label">
          <div class="card shadow-sm text-center"><div class="card-body">
            <div class="display-6 fw-bold">{{ stats[c.key] != null ? stats[c.key] : 0 }}</div>
            <div class="text-muted">{{ c.label }}</div>
          </div></div>
        </div>
      </div>
      <div class="row">
        <div class="col-md-6 mb-3"><div class="card shadow-sm"><div class="card-body">
          <h6>Drives by status</h6>
          <div v-for="(n, s) in stats.drives_by_status" :key="s" class="d-flex justify-content-between">
            <span class="badge" :class="badge(s)">{{ s }}</span><strong>{{ n }}</strong></div>
        </div></div></div>
        <div class="col-md-6 mb-3"><div class="card shadow-sm"><div class="card-body">
          <h6>Applications by status</h6>
          <div v-for="(n, s) in stats.applications_by_status" :key="s" class="d-flex justify-content-between">
            <span class="badge" :class="badge(s)">{{ s }}</span><strong>{{ n }}</strong></div>
        </div></div></div>
      </div>
    </div>

    <!-- Companies -->
    <table v-if="tab === 'companies'" class="table table-hover bg-white shadow-sm">
      <thead class="table-light"><tr><th>Company</th><th>Email</th><th>Drives</th><th>Approval</th><th>Account</th><th></th></tr></thead>
      <tbody>
        <tr v-for="c in companies" :key="c.id">
          <td>{{ c.company_name }}</td><td>{{ c.email }}</td><td>{{ c.drive_count }}</td>
          <td><span class="badge" :class="c.is_approved ? 'bg-success' : 'bg-warning text-dark'">{{ c.is_approved ? 'Approved' : 'Pending' }}</span></td>
          <td><span class="badge" :class="c.active ? 'bg-success' : 'bg-danger'">{{ c.active ? 'Active' : 'Blacklisted' }}</span></td>
          <td class="text-end">
            <button v-if="!c.is_approved" class="btn btn-sm btn-success me-1" @click="companyAction(c, 'approve')">Approve</button>
            <button v-else class="btn btn-sm btn-outline-warning me-1" @click="companyAction(c, 'reject')">Revoke</button>
            <button v-if="c.active" class="btn btn-sm btn-outline-dark me-1" @click="companyAction(c, 'blacklist')">Blacklist</button>
            <button v-else class="btn btn-sm btn-outline-success me-1" @click="companyAction(c, 'activate')">Activate</button>
            <button class="btn btn-sm btn-outline-danger" @click="remove('companies', c.id, c.company_name)">Delete</button>
          </td>
        </tr>
        <tr v-if="!companies.length"><td colspan="6" class="text-center text-muted">No companies found.</td></tr>
      </tbody>
    </table>

    <!-- Students -->
    <table v-if="tab === 'students'" class="table table-hover bg-white shadow-sm">
      <thead class="table-light"><tr><th>Name</th><th>Email</th><th>Branch</th><th>CGPA</th><th>Applications</th><th>Account</th><th></th></tr></thead>
      <tbody>
        <tr v-for="s in students" :key="s.id">
          <td>{{ s.full_name }}</td><td>{{ s.email }}</td><td>{{ s.branch || '-' }}</td>
          <td>{{ s.cgpa != null ? s.cgpa : '-' }}</td><td>{{ s.application_count }}</td>
          <td><span class="badge" :class="s.active ? 'bg-success' : 'bg-danger'">{{ s.active ? 'Active' : 'Blacklisted' }}</span></td>
          <td class="text-end">
            <button v-if="s.active" class="btn btn-sm btn-outline-dark me-1" @click="studentAction(s, 'blacklist')">Blacklist</button>
            <button v-else class="btn btn-sm btn-outline-success me-1" @click="studentAction(s, 'activate')">Activate</button>
            <button class="btn btn-sm btn-outline-danger" @click="remove('students', s.id, s.full_name)">Delete</button>
          </td>
        </tr>
        <tr v-if="!students.length"><td colspan="7" class="text-center text-muted">No students found.</td></tr>
      </tbody>
    </table>

    <!-- Drives -->
    <table v-if="tab === 'drives'" class="table table-hover bg-white shadow-sm">
      <thead class="table-light"><tr><th>Company</th><th>Job</th><th>Deadline</th><th>Applicants</th><th>Status</th><th></th></tr></thead>
      <tbody>
        <tr v-for="d in drives" :key="d.id">
          <td>{{ d.company_name }}</td><td>{{ d.job_title }}</td><td>{{ fmtDate(d.deadline) }}</td><td>{{ d.applicant_count }}</td>
          <td><span class="badge" :class="badge(d.status)">{{ d.status }}</span></td>
          <td class="text-end">
            <button v-if="d.status !== 'Approved'" class="btn btn-sm btn-success me-1" @click="driveStatus(d, 'Approved')">Approve</button>
            <button v-if="d.status === 'Pending'" class="btn btn-sm btn-outline-warning me-1" @click="driveStatus(d, 'Rejected')">Reject</button>
            <button v-if="d.status === 'Approved'" class="btn btn-sm btn-outline-dark me-1" @click="driveStatus(d, 'Closed')">Close</button>
            <button class="btn btn-sm btn-outline-danger" @click="remove('drives', d.id, d.job_title)">Delete</button>
          </td>
        </tr>
        <tr v-if="!drives.length"><td colspan="6" class="text-center text-muted">No drives found.</td></tr>
      </tbody>
    </table>

    <!-- Applications -->
    <table v-if="tab === 'applications'" class="table table-hover bg-white shadow-sm">
      <thead class="table-light"><tr><th>Student</th><th>Company</th><th>Job</th><th>Applied on</th><th>Status</th></tr></thead>
      <tbody>
        <tr v-for="a in applications" :key="a.id">
          <td>{{ a.student_name }}</td><td>{{ a.company_name }}</td><td>{{ a.job_title }}</td>
          <td>{{ fmtDate(a.application_date) }}</td>
          <td><span class="badge" :class="badge(a.status)">{{ a.status }}</span></td>
        </tr>
        <tr v-if="!applications.length"><td colspan="5" class="text-center text-muted">No applications found.</td></tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import api, { errMsg } from '@/api'
import { notify } from '@/store/toast'
import { fmtDate, badge } from '@/utils'

export default {
  name: 'AdminDashboard',
  data() {
    return {
      tab: 'overview',
      tabs: [
        { key: 'overview', label: 'Overview' },
        { key: 'companies', label: 'Companies' },
        { key: 'students', label: 'Students' },
        { key: 'drives', label: 'Drives' },
        { key: 'applications', label: 'Applications' }
      ],
      cards: [
        { key: 'total_students', label: 'Students' },
        { key: 'total_companies', label: 'Companies' },
        { key: 'total_drives', label: 'Drives' },
        { key: 'total_applications', label: 'Applications' }
      ],
      stats: {}, companies: [], students: [], drives: [], applications: [],
      query: '', timer: null
    }
  },
  watch: {
    tab() { this.query = ''; this.load() },
    query() {
      clearTimeout(this.timer)
      this.timer = setTimeout(this.load, 300)
    }
  },
  mounted() { this.load() },
  methods: {
    fmtDate, badge,
    async load() {
      const params = { q: this.query }
      try {
        if (this.tab === 'overview') this.stats = (await api.get('/api/admin/stats')).data
        else this[this.tab] = (await api.get(`/api/admin/${this.tab}`, { params })).data
      } catch (err) { notify(errMsg(err), 'error') }
    },
    async run(request, okMessage) {
      try {
        const res = await request()
        notify((res && res.data && res.data.message) || okMessage)
        this.load()
      } catch (err) { notify(errMsg(err), 'error') }
    },
    companyAction(c, action) { return this.run(() => api.put(`/api/admin/companies/${c.id}/status`, { action })) },
    studentAction(s, action) { return this.run(() => api.put(`/api/admin/students/${s.id}/status`, { action })) },
    driveStatus(d, status) { return this.run(() => api.put(`/api/admin/drives/${d.id}/status`, { status })) },
    remove(kind, id, label) {
      if (!confirm(`Permanently delete "${label}"? Related data will be removed too.`)) return
      return this.run(() => api.delete(`/api/admin/${kind}/${id}`))
    }
  }
}
</script>
