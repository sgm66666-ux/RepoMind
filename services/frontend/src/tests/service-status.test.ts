import { createPinia, setActivePinia } from 'pinia'
import MockAdapter from 'axios-mock-adapter'
import { beforeEach, describe, expect, it } from 'vitest'
import { apiClient } from '../api/client'
import { useServicesStore } from '../stores/services'

const mock = new MockAdapter(apiClient)

beforeEach(() => { mock.reset(); setActivePinia(createPinia()) })

describe('真实服务状态', () => {
  it('checks gateway and forwarded Python route independently', async () => {
    mock.onGet('/api/health').reply(200, { status: 'ok', service: 'java-service' })
    mock.onGet('/api/symbols').reply(503, { message: 'Python service is unavailable' })
    const store = useServicesStore()
    await store.refresh()
    expect(store.gateway).toBe('online')
    expect(store.analysis).toBe('offline')
    expect(store.llm).toBe('unverified')
  })

  it('marks LLM only after a real successful provider response', () => {
    const store = useServicesStore()
    store.recordAgentSuccess('TEST PROVIDER')
    expect(store.llm).toBe('unverified')
    store.recordAgentSuccess('ollama:qwen2.5-coder:14b:json-tool-compat')
    expect(store.llm).toBe('success')
  })
})
