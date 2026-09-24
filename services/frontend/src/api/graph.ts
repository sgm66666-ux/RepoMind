import { apiClient } from './client'
import type { CallGraphResult } from '../models'

export const graphApi = {
  async get(includeUnresolved = false): Promise<CallGraphResult> {
    const { data } = await apiClient.get<CallGraphResult>('/api/call-graph', {
      params: { includeUnresolved },
    })
    return data
  },
}
