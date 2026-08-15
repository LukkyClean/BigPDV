import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.DEV
    ? 'http://localhost:8000/api/v1'
    : `${window.location.origin}/api/v1`,
  timeout: 15000,
})

export default api
