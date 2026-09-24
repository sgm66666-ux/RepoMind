import { apiClient } from './client'

export const healthApi = {
  async gateway(): Promise<boolean> {
    const { data } = await apiClient.get<{ status: string; service: string }>('/api/health')
    return data.status === 'ok' && data.service === 'java-service'
  },
  async analysisService(): Promise<boolean> {
    // Existing gateway route forwards this read-only probe to FastAPI.
    const { data } = await apiClient.get<unknown>('/api/symbols')
    return Array.isArray(data)
  },
}
