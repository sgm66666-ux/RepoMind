import { apiClient } from './client'
import type { FaultLocalizationResult } from '../models'

export const faultApi = {
  async analyze(stackTrace: string): Promise<FaultLocalizationResult> {
    const { data } = await apiClient.post<FaultLocalizationResult>('/api/fault-localization', { stackTrace })
    return data
  },
}
