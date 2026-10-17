import { apiClient } from './client'

export const healthApi = {
  async api(): Promise<boolean> {
    const { data } = await apiClient.get<{ status: string; service: string }>('/api/health')
    return data.status === 'ok' && data.service === 'python-service'
  },
  async analysisService(): Promise<boolean> {
    // Probe the analysis handler separately from process liveness.
    const { data } = await apiClient.get<unknown>('/api/symbols')
    return Array.isArray(data)
  },
}
