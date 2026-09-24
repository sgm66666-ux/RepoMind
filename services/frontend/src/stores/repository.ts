import { defineStore } from 'pinia'
import { demoApi } from '../api/demo'
import { graphApi } from '../api/graph'
import { repositoryApi } from '../api/repository'
import { symbolsApi } from '../api/symbols'
import type { CallGraphResult, CodeSymbol, RepositoryAnalysis } from '../models'
import { errorMessage } from '../utils/errors'

export const useRepositoryStore = defineStore('repository', {
  state: () => ({
    analysis: null as RepositoryAnalysis | null,
    symbols: [] as CodeSymbol[],
    graph: null as CallGraphResult | null,
    loading: false,
    error: null as string | null,
  }),
  actions: {
    async analyze(path: string) {
      this.loading = true
      this.error = null
      try {
        this.analysis = await repositoryApi.analyze(path)
        const [symbols, graph] = await Promise.all([symbolsApi.list(), graphApi.get(false)])
        this.symbols = symbols
        this.graph = graph
        return this.analysis
      } catch (error) {
        this.error = errorMessage(error)
        throw error
      } finally {
        this.loading = false
      }
    },
    async analyzeDemo() {
      const demo = await demoApi.getOrderDemo()
      return this.analyze(demo.repositoryPath)
    },
    async refreshGraph(includeUnresolved: boolean) {
      this.graph = await graphApi.get(includeUnresolved)
    },
  },
})
