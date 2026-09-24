import { describe, expect, it } from 'vitest'
import { filterSymbols } from '../utils/symbols'
import { controllerSymbol, serviceSymbol } from './fixtures'

describe('Symbol filtering', () => {
  it('filters by qualified name, language, and type', () => {
    const pythonFunction = { ...serviceSymbol, id: 'python', language: 'PYTHON' as const, type: 'FUNCTION' as const, qualifiedName: 'service.create_order' }
    const symbols = [controllerSymbol, serviceSymbol, pythonFunction]
    expect(filterSymbols(symbols, { query: 'OrderController', language: 'JAVA', type: 'METHOD' })).toEqual([controllerSymbol])
    expect(filterSymbols(symbols, { query: '', language: 'PYTHON', type: '' })).toEqual([pythonFunction])
  })
})
