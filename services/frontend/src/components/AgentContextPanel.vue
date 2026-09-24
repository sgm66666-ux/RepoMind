<script setup lang="ts">
import type { SymbolContext } from '../models'
import CodeViewer from './CodeViewer.vue'

defineProps<{ context: SymbolContext }>()
</script>

<template>
  <section class="panel context-panel" data-testid="agent-context">
    <div class="section-title-row"><div><span class="eyebrow">代码知识</span><h2>代码上下文</h2></div><span class="context-source">来自现有 Symbol / Call Graph / 源码 API</span></div>
    <div class="context-summary"><strong>Symbol</strong><code>{{ context.targetSymbol.qualifiedName }}</code><span>{{ context.targetSymbol.filePath }}:{{ context.targetSymbol.startLine }}–{{ context.targetSymbol.endLine }}</span></div>
    <div class="detail-grid context-grid">
      <article class="context-block"><span class="eyebrow">调用方</span><p v-if="!context.callers.length">暂无调用方</p><ul><li v-for="item in context.callers" :key="item.relation.id">{{ item.symbol.qualifiedName }}</li></ul></article>
      <article class="context-block"><span class="eyebrow">被调用方</span><p v-if="!context.callees.length">暂无被调用方</p><ul><li v-for="item in context.callees" :key="item.relation.id">{{ item.symbol.qualifiedName }}</li></ul></article>
      <article class="context-block"><span class="eyebrow">关系说明</span><p>仅展示索引与关系 API 返回的代码事实；最终结论由 Agent 单独生成。</p></article>
    </div>
    <div v-if="context.sourceSnippet"><div class="section-title-row"><h3>源码</h3><span class="file-label">{{ context.sourceSnippet.filePath }}</span></div><CodeViewer :content="context.sourceSnippet.content" :start-line="context.sourceSnippet.requestedRange.startLine" /></div>
  </section>
</template>
