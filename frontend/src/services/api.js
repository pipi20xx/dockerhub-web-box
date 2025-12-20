import axios from 'axios'

const apiClient = axios.create({
  // ✨ 直接指向后端API的绝对路径
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json'
  }
})

export default apiClient