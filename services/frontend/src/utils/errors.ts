import { ApiError } from '../api/client'

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 503 && error.message.toLowerCase().includes('provider')) {
      return 'LLM Provider 未配置或配置不完整。'
    }
    if (error.code === 'GATEWAY_UNAVAILABLE') return 'Spring Boot Gateway 无法连接。'
    if (error.message === 'Python service is unavailable') return 'Python Service 无法连接。'
    return `请求失败：${error.message}`
  }
  return error instanceof Error ? `请求失败：${error.message}` : '请求发生未知错误。'
}
