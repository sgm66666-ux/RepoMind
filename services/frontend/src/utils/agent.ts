import type { AgentResponse } from '../models'

export function firstObservedSymbolId(response: AgentResponse): string | null {
  for (const step of response.trace) {
    if (step.tool !== 'searchSymbol' || !step.success || !Array.isArray(step.observation.data)) continue
    const first = step.observation.data[0]
    if (first && typeof first === 'object' && 'id' in first && typeof first.id === 'string') return first.id
  }
  return null
}

export function observationSummary(step: AgentResponse['trace'][number]): string {
  if (!step.success) return step.error?.message || '工具执行失败'
  const data = step.observation.data
  if (step.tool === 'searchSymbol' && Array.isArray(data)) {
    return data.length ? data.map((item) => item?.qualifiedName || item?.name || 'Symbol').join('、') : '未找到匹配的 Symbol'
  }
  if ((step.tool === 'findCallers' || step.tool === 'findCallees') && Array.isArray(data)) {
    return data.length ? data.map((item) => item?.symbol?.qualifiedName || item?.relation?.targetName || '调用关系').join('、') : '未找到调用关系'
  }
  if (step.tool === 'readFile' && data && typeof data === 'object' && 'filePath' in data) {
    return `已读取 ${String(data.filePath)}`
  }
  return step.observation.text || '已返回 Observation'
}
