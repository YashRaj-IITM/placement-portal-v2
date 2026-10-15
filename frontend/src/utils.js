export function fmtDate(iso) {
  return iso ? new Date(iso).toLocaleString() : '-'
}

// ISO (UTC) -> value for <input type="datetime-local"> in the user's timezone
export function toLocalInput(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// <input type="datetime-local"> value -> ISO UTC string
export function fromLocalInput(value) {
  return value ? new Date(value).toISOString() : ''
}

export function badge(status) {
  return {
    Applied: 'bg-primary',
    Shortlisted: 'bg-warning text-dark',
    Selected: 'bg-success',
    Rejected: 'bg-danger',
    Pending: 'bg-secondary',
    Approved: 'bg-success',
    Closed: 'bg-dark'
  }[status] || 'bg-secondary'
}
