import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client'
import { agentApi } from '../api/agent'
import AgentView from '../views/AgentView.vue'
import { createPinia } from 'pinia'

vi.mock('../api/agent', () => ({ agentApi: { run: vi.fn() } }))

describe('Agent provider state', () => {
  it('honestly reports a missing LLM provider', async () => {
    vi.mocked(agentApi.run).mockRejectedValue(new ApiError('No LLM provider configured', 503))
    const wrapper = mount(AgentView, { global: { plugins: [createPinia()] } })
    await wrapper.find('input').setValue('Trace createOrder')
    const button = wrapper.findAll('button').find((item) => item.text() === '运行 Agent')
    await button?.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('LLM Provider 未配置')
    expect(wrapper.text()).toContain('不会使用测试 Provider 代替')
  })
})
