import axios from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 120_000, // LLM 调用可能较慢
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail =
      error?.response?.data?.detail || error?.message || '请求失败'
    ElMessage.error(typeof detail === 'string' ? detail : '请求失败')
    return Promise.reject(error)
  },
)

export default http
