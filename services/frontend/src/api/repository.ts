import { apiClient } from './client'
import type { RepositoryAnalysis } from '../models'

export const repositoryApi = {
  async analyze(path: string): Promise<RepositoryAnalysis> {
    const { data } = await apiClient.post<RepositoryAnalysis>('/api/repositories/analyze', { path })
    return data
  },
}
