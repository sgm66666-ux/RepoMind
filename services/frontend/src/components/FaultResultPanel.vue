<script setup lang="ts">
import { computed } from 'vue'
import type { FaultLocalizationResult } from '../models'
import CodeViewer from './CodeViewer.vue'

const props = defineProps<{ result: FaultLocalizationResult }>()
const sourceEvidence = computed(() => props.result.evidence.find((item) => item.type === 'source')?.content)
const confidenceLabel = computed(() => props.result.confidence === 'HIGH' ? '较高' : props.result.confidence === 'MEDIUM' ? '中等' : '较低')
const statusLabel = computed(() => ({ LOCATED: '已定位', PARTIAL: '部分定位', NOT_FOUND: '未定位' })[props.result.status] || props.result.status)
</script>

<template>
  <section class="fault-result" data-testid="fault-result">
    <div class="result-heading"><div><span class="eyebrow">01 / 异常信息</span><h2>{{ result.exception.exceptionType }}</h2><p>{{ result.exception.message || '未提供异常消息' }}</p></div><el-tag type="warning">定位置信度：{{ confidenceLabel }}</el-tag></div>

    <article class="panel"><span class="eyebrow">02 / Stack Trace · 事实证据</span><h3>运行时堆栈</h3><pre class="stack-trace">{{ result.exception.raw }}</pre></article>

    <article class="panel"><span class="eyebrow">03 / 定位 Symbol · 事实证据</span><h3>{{ result.targetSymbol?.qualifiedName || '未定位到 Symbol' }}</h3><dl class="metadata-list compact"><div><dt>文件</dt><dd>{{ result.targetFile || '—' }}</dd></div><div><dt>堆栈行号</dt><dd>{{ result.stackFrame?.lineNumber ?? '—' }}</dd></div><div><dt>Symbol</dt><dd>{{ result.targetSymbol?.name || '—' }}</dd></div><div><dt>状态</dt><dd>{{ statusLabel }}</dd></div></dl></article>

    <div class="detail-grid context-grid">
      <article class="panel"><span class="eyebrow">04 / 调用关系 · 静态证据</span><h3>调用方</h3><p v-if="!result.callers.length">暂无调用方</p><ul><li v-for="item in result.callers" :key="item.relation.id">{{ item.symbol.qualifiedName }}</li></ul></article>
      <article class="panel"><span class="eyebrow">04 / 调用关系 · 静态证据</span><h3>被调用方</h3><p v-if="!result.callees.length">暂无被调用方</p><ul><li v-for="item in result.callees" :key="item.relation.id">{{ item.symbol.qualifiedName }}</li></ul></article>
      <article class="panel"><span class="eyebrow">04 / 调用关系 · 静态证据</span><h3>引用</h3><p v-if="!result.references.length">暂无引用</p><ul><li v-for="item in result.references" :key="item.id">{{ item.filePath }}:{{ item.line }}</li></ul></article>
    </div>

    <article v-if="sourceEvidence" class="panel"><div class="section-title-row"><div><span class="eyebrow">05 / 源码证据 · 事实</span><h3>定位代码</h3></div><span class="file-label">{{ sourceEvidence.filePath }}</span></div><CodeViewer :content="sourceEvidence.content" :start-line="sourceEvidence.requestedRange.startLine" :highlight-line="result.stackFrame?.lineNumber" /></article>

    <article class="panel explanation-panel"><span class="eyebrow">06 / 根因分析 · 规则推断</span><h3>可能原因</h3><p>{{ result.suspectedCause }}</p><small>此处来自现有确定性故障定位逻辑，不是 LLM 生成结果；仍需结合源码核验。</small></article>
  </section>
</template>
