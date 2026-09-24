<script setup lang="ts">
import { ref } from 'vue'
import { agentApi } from '../api/agent'
import { symbolsApi } from '../api/symbols'
import AgentContextPanel from '../components/AgentContextPanel.vue'
import AgentTrace from '../components/AgentTrace.vue'
import EmptyState from '../components/EmptyState.vue'
import { ApiError } from '../api/client'
import type { AgentResponse, SymbolContext } from '../models'
import { useServicesStore } from '../stores/services'
import { firstObservedSymbolId } from '../utils/agent'
import { errorMessage } from '../utils/errors'

const services = useServicesStore()
const question = ref('')
const submittedQuestion = ref('')
const loading = ref(false)
const response = ref<AgentResponse | null>(null)
const context = ref<SymbolContext | null>(null)
const contextError = ref<string | null>(null)
const requestError = ref<string | null>(null)

async function runAgent() {
  if (!question.value.trim()) return
  loading.value = true
  response.value = null
  context.value = null
  contextError.value = null
  requestError.value = null
  submittedQuestion.value = question.value.trim()
  try {
    const result = await agentApi.run({ question: submittedQuestion.value, maxSteps: 8, timeoutSeconds: 180 })
    response.value = result
    if (result.status === 'COMPLETED') services.recordAgentSuccess(result.provider)
    else services.recordAgentFailure('failed')
    const symbolId = firstObservedSymbolId(result)
    if (symbolId) {
      try { context.value = await symbolsApi.context(symbolId) }
      catch (error) { contextError.value = errorMessage(error) }
    }
  } catch (error) {
    const providerMissing = error instanceof ApiError && error.status === 503 && /provider|配置|configured/i.test(error.message)
    services.recordAgentFailure(providerMissing ? 'unconfigured' : 'failed')
    requestError.value = errorMessage(error)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-stack agent-page">
    <section class="panel agent-prompt"><div class="section-title-row"><div><span class="eyebrow">Agent 执行控制台</span><h2>基于代码证据发起分析</h2></div><span class="console-badge">Tool Calling · 最多 8 步</span></div><p>Agent 根据 Symbol、调用关系和源码 Observation 决定下一步工具调用；这里不模拟对话或预置答案。</p><label class="field-label" for="agent-question">用户问题</label><el-input id="agent-question" v-model="question" size="large" placeholder="输入需要调查的代码问题" @keyup.enter="runAgent" /><div class="prompt-examples"><button @click="question = '为什么InventoryService.checkStock出现NullPointerException？'">为什么 checkStock 出现空指针？</button><button @click="question = '追踪OrderController.createOrder的调用路径。'">追踪 createOrder 调用路径</button></div><div class="form-actions"><el-button type="primary" size="large" :loading="loading" :disabled="!question.trim()" @click="runAgent">运行 Agent</el-button></div></section>

    <div v-if="loading" class="analysis-status loading" role="status"><span class="loading-spinner" />Agent 正在调用真实 LLM 与代码工具；本地模型冷启动可能需要较长时间…</div>
    <el-alert v-if="requestError" :title="requestError" type="warning" :description="services.llm === 'unconfigured' ? '请在 FastAPI 服务中配置 Ollama 或其他真实 Provider。界面不会使用测试 Provider 代替。' : '本次请求未产生可展示的真实 Trace。请检查服务日志后重试。'" :closable="false" show-icon />
    <AgentTrace v-if="response" :response="response" :question="submittedQuestion" />
    <EmptyState v-else-if="!requestError && !loading" title="暂无执行记录" description="运行一次真实 Agent 请求后，这里展示 Tool Call、Observation 和最终回答。" />

    <AgentContextPanel v-if="context" :context="context" />
    <el-alert v-else-if="contextError" :title="`代码上下文加载失败：${contextError}`" type="warning" :closable="false" />
  </div>
</template>
