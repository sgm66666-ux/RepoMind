<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import CallGraphCanvas from '../components/CallGraphCanvas.vue'
import EmptyState from '../components/EmptyState.vue'
import CodeViewer from '../components/CodeViewer.vue'
import { symbolsApi } from '../api/symbols'
import type { CodeSymbol, SymbolContext } from '../models'
import { useRepositoryStore } from '../stores/repository'
import { errorMessage } from '../utils/errors'

const store = useRepositoryStore()
const includeUnresolved = ref(false)
const selected = ref<CodeSymbol | null>(null)
const drawerOpen = ref(false)
const loading = ref(false)
const contextLoading = ref(false)
const context = ref<SymbolContext | null>(null)

async function toggleUnresolved() {
  loading.value = true
  try {
    await store.refreshGraph(includeUnresolved.value)
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    loading.value = false
  }
}

async function selectSymbol(symbol: CodeSymbol) {
  selected.value = symbol
  drawerOpen.value = true
  context.value = null
  contextLoading.value = true
  try {
    context.value = await symbolsApi.context(symbol.id)
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    contextLoading.value = false
  }
}
</script>

<template>
  <div class="page-stack">
    <section class="graph-summary">
      <div><span class="eyebrow">静态调用关系</span><h2>Call Graph</h2><p>实线仅代表 resolved=true 的 CALLS 关系。未解析候选须手动开启，并以虚线显示，不视为确定调用。</p></div>
      <el-switch v-model="includeUnresolved" active-text="显示未解析候选" :loading="loading" @change="toggleUnresolved" />
    </section>
    <template v-if="store.graph?.edges.length">
      <CallGraphCanvas :graph="store.graph" :height="450" @select="selectSymbol" />
      <el-drawer v-model="drawerOpen" size="520px" title="节点详情">
        <div v-if="selected" class="drawer-content" v-loading="contextLoading">
          <div><span class="eyebrow">Symbol</span><h2>{{ selected.qualifiedName }}</h2><dl class="metadata-list"><div><dt>文件</dt><dd>{{ selected.filePath }}</dd></div><div><dt>行号</dt><dd>{{ selected.startLine }}–{{ selected.endLine }}</dd></div><div><dt>类型</dt><dd>{{ selected.type }}</dd></div></dl></div>
          <template v-if="context">
            <section><h3>调用方</h3><p v-if="!context.callers.length">暂无调用方</p><ul><li v-for="item in context.callers" :key="item.relation.id">{{ item.symbol.qualifiedName }}</li></ul></section>
            <section><h3>被调用方</h3><p v-if="!context.callees.length">暂无被调用方</p><ul><li v-for="item in context.callees" :key="item.relation.id">{{ item.symbol.qualifiedName }}</li></ul></section>
            <section v-if="context.sourceSnippet"><h3>源码证据</h3><CodeViewer :content="context.sourceSnippet.content" :start-line="context.sourceSnippet.requestedRange.startLine" /></section>
          </template>
        </div>
      </el-drawer>
    </template>
    <EmptyState v-else title="暂无已解析调用" description="分析含有可解析调用关系的仓库后显示图。" />
  </div>
</template>
