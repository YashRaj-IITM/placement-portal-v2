import { reactive } from 'vue'

export const toast = reactive({ message: '', type: 'success' })
let timer = null

export function notify(message, type = 'success') {
  toast.message = message
  toast.type = type
  clearTimeout(timer)
  timer = setTimeout(() => { toast.message = '' }, 4000)
}
