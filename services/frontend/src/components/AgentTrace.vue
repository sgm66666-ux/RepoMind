<script setup lang="ts">
import type { AgentResponse } from '../models'
import { observationSummary } from '../utils/agent'

defineProps<{ response: AgentResponse; question?: string }>()
const taskLabels: Record<string, string> = {
  RUNTIME_ERROR: '运行时异常',
  BUSINESS_LOGIC_ERROR: '业务逻辑错误',
  CALL_CHAIN_ANALYSIS: '调用链分析',
  CONFIGURATION_ERROR: '配置错误',
}
</script>

<template>
  <section class="agent-result" data-testid="agent-trace">
    <div class="execution-header"><div><span class="eyebrow">Agent 诊断结果</span><h2>本次分析</h2></div><span class="execution-status" :class="response.status === 'COMPLETED' ? 'success' : 'warning'">{{ response.status === 'COMPLETED' ? '已完成' : response.status === 'TIMEOUT' ? '执行超时' : response.status === 'UNSUPPORTED' ? '当前不支持' : response.status === 'NO_PROGRESS' ? '无新证据' : '达到步数上限' }}</span></div>
    <article v-if="question" class="question-panel"><span class="eyebrow">用户问题</span><p>{{ question }}</p></article>

    <article v-if="response.finalDiagnosis" class="panel diagnosis-panel" data-testid="final-diagnosis">
      <header class="diagnosis-heading"><span class="field-label">问题摘要</span><h3>{{ response.finalDiagnosis.summary }}</h3></header>
      <el-alert v-if="response.finalDiagnosis.issue_type === 'BUSINESS_LOGIC_ERROR' && response.executionState?.missing_evidence.includes('business_expectation')" type="warning" title="业务规则证据不足" description="已确认当前源码实现；仓库证据未给出预期计价规则，不能据此确定正确公式。" :closable="false" show-icon />
      <div class="diagnosis-grid">
        <section class="diagnosis-section"><span class="field-label">定位位置 · FACT</span><p class="diagnosis-symbol">{{ response.finalDiagnosis.location.symbol || 'Symbol 未确认' }}</p><span class="diagnosis-location">{{ response.finalDiagnosis.location.file || '文件未确认' }}<template v-if="response.finalDiagnosis.location.line !== null">:{{ response.finalDiagnosis.location.line }}</template></span></section>
        <section class="diagnosis-section"><span class="field-label">原因分析 · INFERENCE</span><p>{{ response.finalDiagnosis.root_cause || '未提供原因分析。' }}</p></section>
      </div>
      <section class="diagnosis-section"><span class="field-label">关键证据 · FACT</span><ul class="diagnosis-evidence"><li v-for="(item, index) in response.finalDiagnosis.evidence" :key="index"><div class="evidence-reference"><strong>{{ item.file || '文件未确认' }}<template v-if="item.line !== null">:{{ item.line }}</template></strong><span v-if="item.symbol">{{ item.symbol }}</span></div><code v-if="item.code">{{ item.code }}</code><span v-else class="evidence-no-code">仅索引记录，未读取源码</span><small>{{ item.reason }}</small></li></ul></section>
      <section class="diagnosis-section"><span class="field-label">调用关系 · 已解析证据</span><p v-if="response.finalDiagnosis.call_chain.length" class="call-chain">{{ response.finalDiagnosis.call_chain.join(' → ') }}</p><p v-else>暂无可核验的调用链。</p><small v-if="response.finalDiagnosis.issue_type === 'CALL_CHAIN_ANALYSIS' && response.finalDiagnosis.call_chain.length">静态调用路径不能证明运行时必然执行。</small></section>
      <div class="diagnosis-grid diagnosis-conclusion"><section class="diagnosis-section"><span class="field-label">修复建议</span><p>{{ response.finalDiagnosis.fix_suggestion || '未提供修复建议。' }}</p></section><section class="diagnosis-section"><span class="field-label">不确定性</span><p>{{ response.finalDiagnosis.uncertainty || '未提供不确定性说明；结论仍需核对。' }}</p></section></div>
    </article>
    <article v-else class="panel diagnosis-fallback" data-testid="diagnosis-fallback"><span class="eyebrow">诊断状态</span><h3>暂未形成可核验的最终诊断</h3><p>{{ response.userMessage || '当前响应未提供有效的 FinalDiagnosis；分析过程已保留。' }}</p></article>

    <details class="panel expert-details" data-testid="expert-details"><summary>查看分析过程 <span>Plan · Tool Calling · Observation（{{ response.trace.length }} 步）</span></summary>
      <article v-if="response.plan" class="agent-plan" data-testid="agent-plan">
        <div class="section-title-row"><div><span class="eyebrow">Agent Plan · 规则生成</span><h3>分析计划</h3></div><span class="file-label">仅提供执行方向，不代表已发现代码证据</span></div>
        <dl class="metadata-list compact"><div><dt>问题类型</dt><dd>{{ taskLabels[response.plan.task_type] || response.plan.task_type }} · {{ response.plan.task_type }}</dd></div><div><dt>分析目标</dt><dd>{{ response.plan.analysis_goal }}</dd></div><div><dt>目标线索</dt><dd>{{ response.plan.target_keywords.join('、') || '待搜索' }}<small v-if="response.plan.target_source === 'HEURISTIC'">（关键词推断，尚未确认 Symbol）</small></dd></div><div><dt>停止条件</dt><dd>{{ response.plan.stop_condition }}</dd></div></dl>
        <div class="plan-tools"><span class="field-label">建议工具顺序</span><span v-for="(tool, index) in response.plan.preferred_tools" :key="`${tool}-${index}`" class="plan-tool"><span v-if="index">→</span><code>{{ tool }}</code></span></div>
      </article>
      <article v-if="response.executionState" class="agent-plan" data-testid="execution-state">
        <div class="section-title-row"><div><span class="eyebrow">Execution Policy · Observation 驱动</span><h3>证据检查</h3></div><span class="file-label">{{ response.executionState.completion_decision }}</span></div>
        <p>缺失证据：{{ response.executionState.missing_evidence.join('、') || '无' }}；重复调用拦截 {{ response.executionState.duplicate_calls }} 次；无进展 {{ response.executionState.no_progress_calls }} 次。</p>
        <p v-if="response.executionState.verified_call_chain.length">已核验调用链：{{ response.executionState.verified_call_chain.join(' → ') }}</p>
        <p v-else-if="response.executionState.partial_call_chain.length > 1">已核验部分路径：{{ response.executionState.partial_call_chain.join(' → ') }}</p>
        <p v-if="response.executionState.policy_events.length">策略事件：{{ response.executionState.policy_events.map(item => `${item.step}. ${item.status}`).join('；') }}</p>
      </article>
      <div class="provider-banner" :class="{ test: response.provider === 'TEST PROVIDER' }"><div><span class="eyebrow">LLM Provider</span><strong>{{ response.provider }}</strong></div><span class="provider-status" :class="{ test: response.provider === 'TEST PROVIDER' }">{{ response.provider === 'TEST PROVIDER' ? '测试 Provider · 非真实 LLM' : '真实响应 · 结论需核验' }}</span></div>
      <div class="trace-section-title"><span class="eyebrow">Tool Calling</span><h3>工具调用与 Observation</h3><span>{{ response.trace.length }} 步</span></div>
      <div v-if="response.trace.length" class="trace-list"><article v-for="step in response.trace" :key="step.step" class="trace-step"><div class="step-index">{{ String(step.step).padStart(2, '0') }}</div><div class="step-body"><div class="section-title-row"><div><span class="eyebrow">Tool Call</span><h3>{{ step.tool }}</h3></div><span class="trace-status" :class="step.policyStatus === 'DUPLICATE_CALL' ? 'warning' : step.success ? 'success' : 'error'">{{ step.policyStatus === 'DUPLICATE_CALL' ? '策略拦截' : step.success ? '成功' : '失败' }}</span></div><p class="observation-summary">{{ observationSummary(step) }}<template v-if="step.progress === false"> · 无新证据</template></p><div class="trace-columns"><div><span class="field-label">调用参数</span><pre>{{ JSON.stringify(step.input, null, 2) }}</pre></div><div><span class="field-label">Observation · 原始数据</span><pre>{{ JSON.stringify(step.observation, null, 2) }}</pre></div></div></div></article></div>
      <div v-else class="empty-inline">暂无 Tool Calling 执行记录。</div>
      <p v-if="response.diagnosisIssues?.length" class="diagnosis-issues">诊断校验备注：{{ response.diagnosisIssues.join('；') }}</p>
    </details>

    <details class="panel raw-details" data-testid="raw-details"><summary>查看原始结果</summary><pre data-testid="raw-model-output">{{ response.rawModelOutput ?? response.answer ?? '模型尚未返回最终内容。' }}</pre></details>
  </section>
</template>
