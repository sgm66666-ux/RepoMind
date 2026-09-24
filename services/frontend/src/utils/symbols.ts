import type { CodeSymbol } from '../models'

export interface LocalSymbolFilters {
  query: string
  language: string
  type: string
}

export function filterSymbols(symbols: CodeSymbol[], filters: LocalSymbolFilters): CodeSymbol[] {
  const query = filters.query.trim().toLowerCase()
  return symbols.filter((symbol) => {
    const matchesQuery = !query || symbol.name.toLowerCase().includes(query) || symbol.qualifiedName.toLowerCase().includes(query)
    const matchesLanguage = !filters.language || symbol.language === filters.language
    const matchesType = !filters.type || symbol.type === filters.type
    return matchesQuery && matchesLanguage && matchesType
  })
}
