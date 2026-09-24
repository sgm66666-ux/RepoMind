import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import FaultResultPanel from '../components/FaultResultPanel.vue'
import { faultFixture } from './fixtures'

describe('Fault result', () => {
  it('separates source evidence from heuristic explanation', () => {
    const wrapper = mount(FaultResultPanel, { props: { result: faultFixture } })
    expect(wrapper.text()).toContain('java.lang.NullPointerException')
    expect(wrapper.text()).toContain('源码证据')
    expect(wrapper.text()).toContain('规则推断')
    expect(wrapper.text()).toContain('InventoryService.java')
    expect(wrapper.find('.code-line.highlighted').exists()).toBe(true)
  })
})
