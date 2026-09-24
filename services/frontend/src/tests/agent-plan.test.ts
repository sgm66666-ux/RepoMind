import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { describe, expect, it } from 'vitest'
import AgentTrace from '../components/AgentTrace.vue'
import type { AgentResponse } from '../models'
import { agentFixture } from './fixtures'

describe('Agent Plan display', () => {
  it('renders the backend plan and Tool Trace only after opening the analysis process', async () => {
    const response: AgentResponse = {
      ...agentFixture,
      plan: {
        task_type: 'BUSINESS_LOGIC_ERROR',
        analysis_goal: '检查订单价格计算逻辑',
        target_keywords: ['calculatePrice'],
        target_source: 'HEURISTIC',
        required_evidence: ['target_method_source', 'caller_context'],
        preferred_tools: ['searchSymbol', 'findCallers', 'readFile'],
        stop_condition: '源码证据充分',
      },
    }
    const wrapper = mount(AgentTrace, { props: { response } })
    const plan = wrapper.get('[data-testid="agent-plan"]')
    const details = wrapper.get('[data-testid="expert-details"]')
    expect((details.element as HTMLDetailsElement).open).toBe(false)
    ;(details.element as HTMLDetailsElement).open = true
    await nextTick()
    expect((details.element as HTMLDetailsElement).open).toBe(true)
    expect(plan.text()).toContain('BUSINESS_LOGIC_ERROR')
    expect(plan.text()).toContain('calculatePrice')
    expect(plan.text()).toContain('关键词推断，尚未确认 Symbol')
    expect(plan.text()).toContain('findCallers')
    expect(wrapper.get('[data-testid="agent-trace"]').text().indexOf('分析计划')).toBeLessThan(wrapper.text().indexOf('工具调用与 Observation'))
  })

  it('does not invent a plan when the response has none', () => {
    const wrapper = mount(AgentTrace, { props: { response: agentFixture } })
    expect(wrapper.find('[data-testid="agent-plan"]').exists()).toBe(false)
  })
})
