import type { ElementDefinition } from 'cytoscape'
import type { CallGraphResult, CodeSymbol } from '../models'

function graphLabel(symbol: CodeSymbol): string {
  if (symbol.type === 'METHOD' || symbol.type === 'FUNCTION') {
    return symbol.qualifiedName.split('.').slice(-2).join('.')
  }
  return symbol.name
}

export function toGraphElements(graph: CallGraphResult): ElementDefinition[] {
  const nodes = new Map<string, CodeSymbol>(graph.nodes.map((symbol) => [symbol.id, symbol]))
  const elements: ElementDefinition[] = graph.nodes.map((symbol) => ({
    data: {
      id: symbol.id,
      label: graphLabel(symbol),
      qualifiedName: symbol.qualifiedName,
      filePath: symbol.filePath,
      startLine: symbol.startLine,
      endLine: symbol.endLine,
      kind: symbol.type === 'CLASS' || symbol.type === 'INTERFACE' ? 'class' : 'method',
      symbol,
    },
  }))

  for (const edge of graph.edges) {
    if (!edge.sourceSymbolId) continue
    let target = edge.targetSymbolId
    if (!target) {
      target = `unresolved:${edge.id}`
      if (!nodes.has(target)) {
        elements.push({ data: { id: target, label: `${edge.targetName} ?`, unresolved: true } })
      }
    }
    elements.push({
      data: { id: edge.id, source: edge.sourceSymbolId, target, resolved: edge.resolved, relation: edge },
      classes: edge.resolved ? 'resolved' : 'unresolved',
    })
  }
  return elements
}
