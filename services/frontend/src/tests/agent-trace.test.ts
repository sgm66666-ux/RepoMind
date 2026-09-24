import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentTrace from '../components/AgentTrace.vue'
import { agentFixture } from './fixtures'

describe('Agent Trace', () => {
  it('preserves Tool Trace and TEST PROVIDER in the expandable analysis process', () => {
    const wrapper = mount(AgentTrace, { props: { response: agentFixture } })
    expect(wrapper.text()).toContain('searchSymbol')
    expect(wrapper.text()).toContain('Observation')
    expect(wrapper.text()).toContain('TEST PROVIDER')
    expect(wrapper.text()).toContain('非真实 LLM')
    expect(wrapper.get('.execution-status').text()).toBe('已完成')
    expect(wrapper.get('.trace-step').text()).toContain('成功')
    expect(wrapper.get('.provider-status.test').text()).toContain('非真实 LLM')
    expect(wrapper.get('[data-testid="expert-details"]').element).not.toHaveProperty('open', true)
    expect(wrapper.get('[data-testid="diagnosis-fallback"]').text()).toContain('暂未形成可核验的最终诊断')
  })

  it('shows unsupported and execution-policy facts without claiming a completed diagnosis', () => {
    const wrapper = mount(AgentTrace, { props: { response: {
      ...agentFixture,
      status: 'UNSUPPORTED',
      trace: [],
      answer: null,
      finalDiagnosis: null,
      userMessage: '当前工具链无法读取配置文件。',
      executionState: {
        evidence_checklist: { configuration_source: false },
        missing_evidence: ['configuration_source'],
        verified_call_chain: [], partial_call_chain: [],
        duplicate_calls: 0, no_progress_calls: 0,
        policy_events: [{ step: 0, status: 'UNSUPPORTED', message: 'No configuration reader.' }],
        completion_decision: 'UNSUPPORTED',
      },
    } } })
    expect(wrapper.text()).toContain('当前不支持')
    expect(wrapper.get('[data-testid="diagnosis-fallback"]').text()).toContain('无法读取配置文件')
    expect(wrapper.get('[data-testid="execution-state"]').text()).toContain('configuration_source')
    expect(wrapper.get('[data-testid="expert-details"]').element).not.toHaveProperty('open', true)
  })
})
