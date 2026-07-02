import axios from 'axios'
import { ElMessage } from 'element-plus'
import { demoAdapter, isStaticDemo } from './demo'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 120_000,
  adapter: isStaticDemo() ? demoAdapter : undefined,
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (isStaticDemo()) {
      return Promise.reject(error)
    }

    const detail =
      error?.response?.data?.detail || error?.message || '请求失败'
    ElMessage.error(typeof detail === 'string' ? detail : '请求失败')
    return Promise.reject(error)
  },
)

export default http
