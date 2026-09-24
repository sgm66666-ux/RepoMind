import { apiClient } from './client'
import type { CodeSymbol, FileReadResult, SymbolContext } from '../models'

export interface SymbolFilters {
  query?: string
  name?: string
  qualifiedName?: string
  type?: string
  language?: string
}

export const symbolsApi = {
  async list(filters: SymbolFilters = {}): Promise<CodeSymbol[]> {
    const { data } = await apiClient.get<CodeSymbol[]>('/api/symbols', { params: filters })
    return data
  },
  async context(symbolId: string): Promise<SymbolContext> {
    const { data } = await apiClient.post<SymbolContext>('/api/context', { symbolId })
    return data
  },
  async readFile(filePath: string, startLine?: number, endLine?: number): Promise<FileReadResult> {
    const { data } = await apiClient.get<FileReadResult>('/api/files/read', {
      params: { filePath, startLine, endLine },
    })
    return data
  },
}
