import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { describe, expect, it } from 'vitest'
import AgentTrace from '../components/AgentTrace.vue'
import type { AgentResponse } from '../models'
import { agentFixture } from './fixtures'

const raw = '{"issue_type":"BUSINESS_LOGIC_ERROR","root_cause":"raw-only-marker"}'
const response: AgentResponse = {
  ...agentFixture,
  rawModelOutput: raw,
  executionState: {
    evidence_checklist: { business_expectation: false }, missing_evidence: ['business_expectation'],
    verified_call_chain: [], partial_call_chain: [], duplicate_calls: 0, no_progress_calls: 0,
    policy_events: [], completion_decision: 'PARTIAL',
  },
  diagnosisStatus: 'VALID',
  finalDiagnosis: {
    issue_type: 'BUSINESS_LOGIC_ERROR',
    summary: '已定位价格实现',
    location: { file: 'src/PriceService.java', line: 8, symbol: 'PriceService.calculatePrice' },
    evidence: [{ file: 'src/PriceService.java', line: 8, symbol: 'PriceService.calculatePrice',
      code: 'return price + quantity * discount;', reason: 'readFile 返回的源码', kind: 'FACT', source_tool: 'readFile', source_step: 3 }],
    call_chain: ['OrderService.createOrder', 'PriceService.calculatePrice'],
    root_cause: '当前公式可能不符合业务规则。',
    root_cause_kind: 'INFERENCE',
    fix_suggestion: '先核对业务规则。',
    uncertainty: '尚无产品需求证据。',
  },
}

describe('user-facing FinalDiagnosis', () => {
  it('shows a readable diagnosis and keeps raw JSON closed by default', () => {
    const wrapper = mount(AgentTrace, { props: { response } })
    expect(wrapper.get('[data-testid="final-diagnosis"]').text()).toContain('已定位价格实现')
    expect(wrapper.get('[data-testid="final-diagnosis"]').text()).toContain('return price + quantity * discount;')
    expect((wrapper.get('[data-testid="raw-details"]').element as HTMLDetailsElement).open).toBe(false)
    expect((wrapper.get('[data-testid="expert-details"]').element as HTMLDetailsElement).open).toBe(false)
    expect(wrapper.get('[data-testid="raw-model-output"]').text()).toContain('raw-only-marker')
    expect(wrapper.get('[data-testid="final-diagnosis"]').text()).toContain('业务规则证据不足')
  })

  it('reveals actual Plan/Observation and raw model output only when opened', async () => {
    const wrapper = mount(AgentTrace, { props: { response } })
    ;(wrapper.get('[data-testid="expert-details"]').element as HTMLDetailsElement).open = true
    ;(wrapper.get('[data-testid="raw-details"]').element as HTMLDetailsElement).open = true
    await nextTick()
    expect((wrapper.get('[data-testid="expert-details"]').element as HTMLDetailsElement).open).toBe(true)
    expect(wrapper.get('[data-testid="expert-details"]').text()).toContain('Observation')
    expect((wrapper.get('[data-testid="raw-details"]').element as HTMLDetailsElement).open).toBe(true)
    expect(wrapper.get('[data-testid="raw-model-output"]').text()).toContain(raw)
  })
})
