import { apiClient } from './client'
import type { AgentRequest, AgentResponse } from '../models'

export const agentApi = {
  async run(request: AgentRequest): Promise<AgentResponse> {
    const { data } = await apiClient.post<AgentResponse>('/api/agent/chat', request, { timeout: (request.timeoutSeconds + 10) * 1000 })
    return data
  },
}
