import { describe, expect, it } from 'vitest'
import { toGraphElements } from '../utils/graph'
import { graphFixture, resolvedCall } from './fixtures'

describe('Call Graph conversion', () => {
  it('uses resolved CALLS relations as solid graph edges', () => {
    const elements = toGraphElements(graphFixture)
    const edge = elements.find((element) => element.data.id === resolvedCall.id)
    const source = elements.find((element) => element.data.id === resolvedCall.sourceSymbolId)
    expect(edge?.classes).toBe('resolved')
    expect(edge?.data.source).toBe(resolvedCall.sourceSymbolId)
    expect(edge?.data.target).toBe(resolvedCall.targetSymbolId)
    expect(source?.data.label).toBe('OrderController.createOrder')
  })

  it('marks unresolved relations and creates a distinct placeholder node', () => {
    const unresolved = { ...resolvedCall, id: 'unknown-call', targetSymbolId: null, targetName: 'unknownMethod', resolved: false }
    const elements = toGraphElements({ ...graphFixture, edges: [unresolved] })
    expect(elements.find((element) => element.data.id === 'unknown-call')?.classes).toBe('unresolved')
    expect(elements.some((element) => element.data.id === 'unresolved:unknown-call')).toBe(true)
  })
})
