import { defineStore } from 'pinia'
import { healthApi } from '../api/health'

export type ServiceStatus = 'checking' | 'online' | 'offline'
export type LlmStatus = 'unverified' | 'success' | 'unconfigured' | 'failed'

export const useServicesStore = defineStore('services', {
  state: () => ({
    gateway: 'checking' as ServiceStatus,
    analysis: 'checking' as ServiceStatus,
    llm: 'unverified' as LlmStatus,
    provider: null as string | null,
  }),
  actions: {
    async refresh() {
      const [gateway, analysis] = await Promise.allSettled([healthApi.gateway(), healthApi.analysisService()])
      this.gateway = gateway.status === 'fulfilled' && gateway.value ? 'online' : 'offline'
      this.analysis = analysis.status === 'fulfilled' && analysis.value ? 'online' : 'offline'
    },
    recordAgentSuccess(provider: string) {
      this.provider = provider
      this.llm = provider === 'TEST PROVIDER' ? 'unverified' : 'success'
    },
    recordAgentFailure(kind: 'unconfigured' | 'failed') {
      this.provider = null
      this.llm = kind
    },
  },
})
