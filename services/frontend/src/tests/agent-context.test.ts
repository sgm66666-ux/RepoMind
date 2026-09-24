import { describe, expect, it } from 'vitest'
import { firstObservedSymbolId, observationSummary } from '../utils/agent'
import { agentFixture, controllerSymbol } from './fixtures'

describe('Agent 代码上下文', () => {
  it('uses only a Symbol ID observed in the actual trace', () => {
    expect(firstObservedSymbolId(agentFixture)).toBe(controllerSymbol.id)
    expect(observationSummary(agentFixture.trace[0])).toContain(controllerSymbol.qualifiedName)
    expect(firstObservedSymbolId({ ...agentFixture, trace: [] })).toBeNull()
  })
})
