<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import CallGraphCanvas from '../components/CallGraphCanvas.vue'
import EmptyState from '../components/EmptyState.vue'
import StatCard from '../components/StatCard.vue'
import type { CodeSymbol } from '../models'
import { useRepositoryStore } from '../stores/repository'
import { useServicesStore } from '../stores/services'
import { errorMessage } from '../utils/errors'

const repository = useRepositoryStore()
const services = useServicesStore()
const router = useRouter()
const gatewayStatus = computed(() => services.gateway === 'online' ? '正常' : services.gateway === 'offline' ? '离线' : '检测中')
const analysisStatus = computed(() => services.analysis === 'online' ? '正常' : services.analysis === 'offline' ? '离线' : '检测中')
const llmStatus = computed(() => services.llm === 'success' ? '本次调用成功' : services.llm === 'unconfigured' ? '未配置' : services.llm === 'failed' ? '调用失败' : '未验证')

async function analyzeDemo() {
  try {
    await repository.analyzeDemo()
    ElMessage.success('演示仓库分析完成')
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

function openSymbol(symbol: CodeSymbol) {
  router.push({ name: 'symbols', query: { symbol: symbol.id } })
}
</script>

<template>
  <div class="page-stack">
    <section class="intro-panel">
      <div><span class="eyebrow">代码分析工作台</span><h2>代码分析与故障调查</h2><p>基于 AST、Symbol 与 Call Graph 建立代码索引；Agent 通过 Tool Calling 查阅相关证据。</p></div>
      <div class="intro-actions"><el-button type="primary" :loading="repository.loading" @click="analyzeDemo">分析演示仓库</el-button><el-button @click="router.push('/repository')">打开代码仓库</el-button></div>
    </section>

    <section>
      <div class="section-title-row"><div><span class="eyebrow">服务状态</span><h2>运行环境</h2></div><el-button text @click="services.refresh()">刷新状态</el-button></div>
      <div class="service-grid">
        <article class="service-card"><div><span class="service-icon">GW</span><strong>Spring Boot Gateway</strong></div><span class="status-pill" :class="services.gateway">{{ gatewayStatus }}</span><small>来自 /api/health 的实时响应</small></article>
        <article class="service-card"><div><span class="service-icon">PY</span><strong>Python Service</strong></div><span class="status-pill" :class="services.analysis">{{ analysisStatus }}</span><small>通过 Gateway 的 /api/symbols 探测</small></article>
        <article class="service-card"><div><span class="service-icon">LLM</span><strong>Ollama / LLM</strong></div><span class="status-pill" :class="services.llm">{{ llmStatus }}</span><small>{{ services.provider || '现有 API 无独立 LLM 健康状态；需真实调用验证' }}</small></article>
      </div>
    </section>

    <section>
      <div class="section-title-row"><div><span class="eyebrow">当前索引</span><h2>仓库分析摘要</h2></div><span v-if="repository.analysis" class="file-label">{{ repository.analysis.repositoryPath }}</span></div>
      <div v-if="repository.analysis" class="stats-grid">
        <StatCard label="代码文件" :value="repository.analysis.sourceFileCount" hint="Java / Python" />
        <StatCard label="Symbol 数量" :value="repository.analysis.symbolCount" hint="结构化定义" />
        <StatCard label="Relation 数量" :value="repository.analysis.relationCount" hint="静态关系" />
        <StatCard label="Resolved Calls" :value="repository.analysis.resolvedCallCount" hint="已解析调用" />
        <StatCard label="未解析调用" :value="repository.analysis.unresolvedCallCount" hint="不作为确定调用展示" />
      </div>
      <EmptyState v-else title="尚未分析仓库" description="输入本地仓库路径，或分析项目内的真实 order-demo。" />
    </section>

    <section class="pipeline-panel" aria-label="分析流程"><span v-for="(step, index) in ['仓库', 'AST', 'Symbol', 'Relation', 'Call Graph', 'Agent']" :key="step" class="pipeline-step"><b>{{ step }}</b><i v-if="index < 5">→</i></span></section>

    <section>
      <div class="section-title-row"><div><span class="eyebrow">静态调用关系</span><h2>Call Graph 预览</h2></div><el-button text @click="router.push('/call-graph')">查看完整关系图 →</el-button></div>
      <CallGraphCanvas v-if="repository.graph?.edges.length" :graph="repository.graph" :height="340" @select="openSymbol" />
      <EmptyState v-else title="暂无已解析调用" description="完成仓库分析后展示由真实 Relation 构建的图。" />
    </section>
  </div>
</template>
