import type { AgentResponse, CallGraphResult, CodeSymbol, FaultLocalizationResult, Relation, RepositoryAnalysis } from '../models'

export const controllerSymbol: CodeSymbol = {
  id: 'OrderController.java:10:12:METHOD:demo.order.OrderController.createOrder',
  name: 'createOrder',
  qualifiedName: 'demo.order.OrderController.createOrder',
  type: 'METHOD',
  language: 'JAVA',
  filePath: 'OrderController.java',
  startLine: 10,
  endLine: 12,
  parentSymbolId: null,
  signature: 'createOrder()',
  module: 'demo.order',
}

export const serviceSymbol: CodeSymbol = {
  ...controllerSymbol,
  id: 'OrderService.java:10:12:METHOD:demo.order.OrderService.createOrder',
  qualifiedName: 'demo.order.OrderService.createOrder',
  filePath: 'OrderService.java',
}

export const resolvedCall: Relation = {
  id: 'resolved-call',
  sourceSymbolId: controllerSymbol.id,
  targetSymbolId: serviceSymbol.id,
  targetName: 'createOrder',
  type: 'CALLS',
  filePath: 'OrderController.java',
  line: 11,
  resolved: true,
  evidence: 'orderService.createOrder()',
}

export const graphFixture: CallGraphResult = {
  nodes: [controllerSymbol, serviceSymbol],
  edges: [resolvedCall],
  resolvedCallCount: 1,
  unresolvedCallCount: 0,
}

export const analysisFixture: RepositoryAnalysis = {
  repositoryPath: 'D:/Projects/RepoMind/demo/order-demo',
  sourceFileCount: 6,
  symbolCount: 14,
  relationCount: 17,
  resolvedCallCount: 4,
  unresolvedCallCount: 0,
  languageBreakdown: { JAVA: 6 },
  scanIssues: [],
}

export const faultFixture: FaultLocalizationResult = {
  exception: { exceptionType: 'java.lang.NullPointerException', message: 'stock is null', frames: [], raw: 'trace' },
  targetFile: 'InventoryService.java',
  targetSymbol: { ...serviceSymbol, name: 'checkStock', qualifiedName: 'demo.order.InventoryService.checkStock', filePath: 'InventoryService.java', startLine: 10, endLine: 15 },
  lineRange: { startLine: 10, endLine: 15 },
  stackFrame: { className: 'demo.order.InventoryService', methodName: 'checkStock', fileName: 'InventoryService.java', lineNumber: 12, raw: 'frame', projectFrame: true },
  callers: [{ symbol: serviceSymbol, relation: resolvedCall }],
  callees: [],
  references: [],
  evidence: [{ type: 'source', content: { filePath: 'InventoryService.java', language: 'JAVA', requestedRange: { startLine: 10, endLine: 15 }, content: 'void checkStock() {\n  stock.available;\n}' } }],
  suspectedCause: 'The target dereferences a null value returned by a callee.',
  confidence: 'HIGH',
  status: 'LOCATED',
}

export const agentFixture: AgentResponse = {
  status: 'COMPLETED',
  provider: 'TEST PROVIDER',
  trace: [
    {
      step: 1,
      tool: 'searchSymbol',
      input: { qualifiedName: controllerSymbol.qualifiedName },
      observation: { tool: 'searchSymbol', success: true, data: [controllerSymbol], error: null, text: 'searchSymbol executed successfully' },
      observationText: 'searchSymbol executed successfully',
      success: true,
      output: [controllerSymbol],
      error: null,
    },
  ],
  answer: 'TEST PROVIDER: evidence collected.',
}
