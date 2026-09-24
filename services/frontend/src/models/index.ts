export type Language = 'JAVA' | 'PYTHON'
export type SymbolType = 'CLASS' | 'INTERFACE' | 'METHOD' | 'FUNCTION'
export type RelationType = 'IMPORTS' | 'EXTENDS' | 'IMPLEMENTS' | 'CALLS' | 'REFERENCES'

export interface RepositoryAnalysis {
  repositoryPath: string
  sourceFileCount: number
  symbolCount: number
  relationCount: number
  resolvedCallCount: number
  unresolvedCallCount: number
  languageBreakdown: Record<string, number>
  scanIssues: Array<{ filePath: string; message: string }>
}

export interface CodeSymbol {
  id: string
  name: string
  qualifiedName: string
  type: SymbolType
  language: Language
  filePath: string
  startLine: number
  endLine: number
  parentSymbolId: string | null
  signature: string | null
  module: string | null
}

export interface Relation {
  id: string
  sourceSymbolId: string | null
  targetSymbolId: string | null
  targetName: string
  type: RelationType
  filePath: string
  line: number
  resolved: boolean
  evidence: string
}

export interface GraphConnection {
  symbol: CodeSymbol
  relation: Relation
}

export interface CallGraphResult {
  nodes: CodeSymbol[]
  edges: Relation[]
  resolvedCallCount: number
  unresolvedCallCount: number
}

export interface FileReadResult {
  filePath: string
  language: Language
  requestedRange: { startLine: number; endLine: number }
  content: string
}

export interface SymbolContext {
  targetSymbol: CodeSymbol
  sourceSnippet: FileReadResult | null
  parent: CodeSymbol | null
  imports: Relation[]
  callers: GraphConnection[]
  callees: GraphConnection[]
  references: Relation[]
  evidence: Array<Record<string, unknown>>
}

export interface StackFrame {
  className: string | null
  methodName: string | null
  fileName: string | null
  lineNumber: number | null
  raw: string
  projectFrame: boolean
}

export interface FaultEvidence {
  type?: string
  filePath?: string
  line?: number
  lineRange?: { startLine: number; endLine: number }
  content?: FileReadResult
  [key: string]: unknown
}

export interface FaultLocalizationResult {
  exception: { exceptionType: string; message: string | null; frames: StackFrame[]; raw: string }
  targetFile: string | null
  targetSymbol: CodeSymbol | null
  lineRange: { startLine: number; endLine: number } | null
  stackFrame: StackFrame | null
  callers: GraphConnection[]
  callees: GraphConnection[]
  references: Relation[]
  evidence: FaultEvidence[]
  suspectedCause: string
  confidence: string
  status: string
}

export interface Observation {
  tool: string
  success: boolean
  data: unknown
  error: { code: string; message: string } | null
  text: string
}

export interface AgentStep {
  step: number
  tool: string
  input: Record<string, unknown>
  observation: Observation
  observationText: string
  success: boolean
  output: unknown
  error: { code: string; message: string } | null
  progress?: boolean
  newEvidence?: string[]
  policyStatus?: string | null
  toolExecuted?: boolean
}

export interface AgentExecutionState {
  evidence_checklist: Record<string, boolean>
  missing_evidence: string[]
  verified_call_chain: string[]
  partial_call_chain: string[]
  duplicate_calls: number
  no_progress_calls: number
  policy_events: Array<{ step: number; status: string; message: string; tool?: string }>
  completion_decision: 'COMPLETE' | 'PARTIAL' | 'INSUFFICIENT_EVIDENCE' | 'UNSUPPORTED'
}

export interface AgentRequest {
  question: string
  maxSteps: number
  timeoutSeconds: number
}

export interface AgentPlan {
  task_type: 'RUNTIME_ERROR' | 'BUSINESS_LOGIC_ERROR' | 'CALL_CHAIN_ANALYSIS' | 'CONFIGURATION_ERROR'
  analysis_goal: string
  target_keywords: string[]
  target_source: 'QUERY' | 'HEURISTIC' | 'UNSPECIFIED'
  required_evidence: string[]
  preferred_tools: string[]
  stop_condition: string
}

export interface FinalDiagnosisEvidence {
  file: string | null
  line: number | null
  symbol: string | null
  code: string | null
  reason: string
  kind: 'FACT'
  source_tool: string | null
  source_step: number | null
}

export interface FinalDiagnosis {
  issue_type: AgentPlan['task_type']
  summary: string
  location: { file: string | null; line: number | null; symbol: string | null }
  root_cause: string
  root_cause_kind: 'INFERENCE'
  evidence: FinalDiagnosisEvidence[]
  call_chain: string[]
  fix_suggestion: string
  uncertainty: string
}

export interface AgentResponse {
  status: 'COMPLETED' | 'TIMEOUT' | 'MAX_STEPS' | 'NO_PROGRESS' | 'UNSUPPORTED'
  provider: string
  trace: AgentStep[]
  answer: string | null
  plan?: AgentPlan
  finalDiagnosis?: FinalDiagnosis | null
  diagnosisStatus?: 'VALID' | 'INVALID_FORMAT' | 'INSUFFICIENT_EVIDENCE' | 'NOT_COMPLETED' | 'UNSUPPORTED'
  diagnosisIssues?: string[]
  userMessage?: string | null
  rawModelOutput?: string | null
  completionDecision?: AgentExecutionState['completion_decision']
  executionState?: AgentExecutionState
}

export interface DemoInfo {
  repositoryPath: string
  stackTrace: string
}
