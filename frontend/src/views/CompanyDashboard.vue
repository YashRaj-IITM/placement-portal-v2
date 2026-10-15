<template>
  <div class="container py-4">
    <h2 class="mb-3">Company Dashboard</h2>
    <div v-if="!profile.is_approved" class="alert alert-warning">
      Your company is awaiting admin approval. You can edit your profile, but you cannot create drives yet.
    </div>

    <ul class="nav nav-tabs mb-4">
      <li class="nav-item" v-for="t in tabs" :key="t.key">
        <a class="nav-link" :class="{ active: tab === t.key }" href="#" @click.prevent="tab = t.key">{{ t.label }}</a>
      </li>
    </ul>

    <!-- Profile -->
    <div v-if="tab === 'profile'" class="card shadow-sm p-4" style="max-width: 600px">
      <form @submit.prevent="saveProfile">
        <div class="mb-3"><label class="form-label">Company name</label>
          <input class="form-control" v-model="profile.company_name" required minlength="2" /></div>
        <div class="mb-3"><label class="form-label">HR contact</label>
          <input class="form-control" v-model="profile.hr_contact" /></div>
        <div class="mb-3"><label class="form-label">Website</label>
          <input type="url" class="form-control" v-model="profile.website" placeholder="https://..." /></div>
        <button class="btn btn-primary">Save profile</button>
      </form>
    </div>

    <!-- Drives -->
    <div v-if="tab === 'drives'">
      <div class="d-flex justify-content-between mb-3">
        <h5 class="mb-0">My Placement Drives</h5>
        <button class="btn btn-primary" :disabled="!profile.is_approved" @click="openForm()">+ New drive</button>
      </div>

      <div v-if="showForm" class="card shadow-sm p-4 mb-4">
        <h5>{{ editingId ? 'Edit drive' : 'Create drive' }}</h5>
        <form @submit.prevent="saveDrive">
          <div class="row">
            <div class="col-md-6 mb-3"><label class="form-label">Job title</label>
              <input class="form-control" v-model="drive.job_title" required minlength="3" /></div>
            <div class="col-md-6 mb-3"><label class="form-label">Application deadline</label>
              <input type="datetime-local" class="form-control" v-model="drive.deadline" required /></div>
          </div>
          <div class="mb-3"><label class="form-label">Job description</label>
            <textarea class="form-control" rows="3" v-model="drive.job_description" required minlength="10"></textarea></div>
          <div class="row">
            <div class="col-md-4 mb-3"><label class="form-label">Eligible branches (comma separated)</label>
              <input class="form-control" v-model="drive.eligible_branches" placeholder="CSE, ECE" /></div>
            <div class="col-md-4 mb-3"><label class="form-label">Minimum CGPA</label>
              <input type="number" step="0.1" min="0" max="10" class="form-control" v-model="drive.min_cgpa" /></div>
            <div class="col-md-4 mb-3"><label class="form-label">Eligible graduation years</label>
              <input class="form-control" v-model="drive.eligible_years" placeholder="2026, 2027" /></div>
          </div>
          <button class="btn btn-success me-2">{{ editingId ? 'Update' : 'Create' }}</button>
          <button type="button" class="btn btn-outline-secondary" @click="showForm = false">Cancel</button>
          <small v-if="editingId" class="text-muted ms-3">Edited drives go back to "Pending" for admin approval.</small>
        </form>
      </div>

      <table class="table table-hover bg-white shadow-sm">
        <thead class="table-light"><tr><th>Title</th><th>Deadline</th><th>Status</th><th>Applicants</th><th></th></tr></thead>
        <tbody>
          <tr v-for="d in drives" :key="d.id">
            <td>{{ d.job_title }}</td><td>{{ fmtDate(d.deadline) }}</td>
            <td><span class="badge" :class="badge(d.status)">{{ d.status }}</span></td>
            <td>{{ d.applicant_count }}</td>
            <td class="text-end">
              <button class="btn btn-sm btn-outline-primary me-1" @click="viewApplicants(d)">Applicants</button>
              <button class="btn btn-sm btn-outline-secondary me-1" :disabled="d.status === 'Closed'" @click="openForm(d)">Edit</button>
              <button class="btn btn-sm btn-outline-danger" @click="removeDrive(d)">Delete</button>
            </td>
          </tr>
          <tr v-if="!drives.length"><td colspan="5" class="text-center text-muted">No drives yet.</td></tr>
        </tbody>
      </table>
    </div>

    <!-- Applicants -->
    <div v-if="tab === 'applicants'">
      <h5 class="mb-3">Applicants <span v-if="selectedDrive">for "{{ selectedDrive.job_title }}"</span></h5>
      <p v-if="!selectedDrive" class="text-muted">Open the Drives tab and click "Applicants" on a drive.</p>
      <table v-else class="table table-hover bg-white shadow-sm">
        <thead class="table-light"><tr><th>Student</th><th>Branch</th><th>CGPA</th><th>Year</th><th>Resume</th><th>Status</th><th>Update</th></tr></thead>
        <tbody>
          <tr v-for="a in applicants" :key="a.application_id">
            <td>{{ a.student_name }}<br /><small class="text-muted">{{ a.student_email }}</small></td>
            <td>{{ a.branch || '-' }}</td><td>{{ a.cgpa != null ? a.cgpa : '-' }}</td><td>{{ a.graduation_year || '-' }}</td>
            <td><a v-if="a.resume_path" :href="a.resume_path" target="_blank" rel="noopener">View</a><span v-else>-</span></td>
            <td><span class="badge" :class="badge(a.status)">{{ a.status }}</span></td>
            <td>
              <button v-for="s in ['Shortlisted', 'Selected', 'Rejected']" :key="s" class="btn btn-sm btn-outline-dark me-1 mb-1"
                      :disabled="a.status === s" @click="setStatus(a, s)">{{ s }}</button>
            </td>
          </tr>
          <tr v-if="!applicants.length"><td colspan="7" class="text-center text-muted">No applicants yet.</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import api, { errMsg } from '@/api'
import { notify } from '@/store/toast'
import { fmtDate, badge, toLocalInput, fromLocalInput } from '@/utils'

const blankDrive = () => ({ job_title: '', job_description: '', eligible_branches: '', min_cgpa: 0, eligible_years: '', deadline: '' })

export default {
  name: 'CompanyDashboard',
  data() {
    return {
      tab: 'drives',
      tabs: [
        { key: 'profile', label: 'Company Profile' },
        { key: 'drives', label: 'Drives' },
        { key: 'applicants', label: 'Applicants' }
      ],
      profile: {}, drives: [], applicants: [], selectedDrive: null,
      showForm: false, editingId: null, drive: blankDrive()
    }
  },
  watch: { tab(t) { if (t === 'drives') this.loadDrives() } },
  async mounted() {
    try {
      await this.loadProfile()
      await this.loadDrives()
    } catch (err) { notify(errMsg(err), 'error') }
  },
  methods: {
    fmtDate, badge,
    async loadProfile() { this.profile = (await api.get('/api/company/profile')).data },
    async loadDrives() {
      try { this.drives = (await api.get('/api/company/drives')).data } catch (err) { notify(errMsg(err), 'error') }
    },
    async saveProfile() {
      try {
        const { company_name, hr_contact, website } = this.profile
        await api.put('/api/company/profile', { company_name, hr_contact, website })
        notify('Profile updated')
      } catch (err) { notify(errMsg(err), 'error') }
    },
    openForm(d) {
      this.editingId = d ? d.id : null
      this.drive = d
        ? { ...d, deadline: toLocalInput(d.deadline) }
        : blankDrive()
      this.showForm = true
    },
    async saveDrive() {
      const payload = {
        job_title: this.drive.job_title,
        job_description: this.drive.job_description,
        eligible_branches: this.drive.eligible_branches,
        min_cgpa: this.drive.min_cgpa,
        eligible_years: this.drive.eligible_years,
        application_deadline: fromLocalInput(this.drive.deadline)
      }
      try {
        const res = this.editingId
          ? await api.put(`/api/company/drives/${this.editingId}`, payload)
          : await api.post('/api/company/drives', payload)
        notify(res.data.message)
        this.showForm = false
        this.loadDrives()
      } catch (err) { notify(errMsg(err, 'Could not save drive'), 'error') }
    },
    async removeDrive(d) {
      if (!confirm(`Delete "${d.job_title}" and all its applications?`)) return
      try {
        await api.delete(`/api/company/drives/${d.id}`)
        notify('Drive deleted')
        this.loadDrives()
      } catch (err) { notify(errMsg(err), 'error') }
    },
    async viewApplicants(d) {
      this.selectedDrive = d
      this.tab = 'applicants'
      try { this.applicants = (await api.get(`/api/company/drives/${d.id}/applications`)).data } catch (err) { notify(errMsg(err), 'error') }
    },
    async setStatus(a, status) {
      try {
        await api.put(`/api/company/applications/${a.application_id}/status`, { status })
        a.status = status
        notify(`Marked ${status}; the student will be emailed`)
      } catch (err) { notify(errMsg(err), 'error') }
    }
  }
}
</script>
