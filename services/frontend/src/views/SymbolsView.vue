<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute } from 'vue-router'
import CodeViewer from '../components/CodeViewer.vue'
import EmptyState from '../components/EmptyState.vue'
import { symbolsApi } from '../api/symbols'
import type { CodeSymbol, SymbolContext } from '../models'
import { useRepositoryStore } from '../stores/repository'
import { errorMessage } from '../utils/errors'
import { filterSymbols } from '../utils/symbols'

const store = useRepositoryStore()
const route = useRoute()
const query = ref('')
const language = ref('')
const type = ref('')
const drawerOpen = ref(false)
const contextLoading = ref(false)
const selected = ref<CodeSymbol | null>(null)
const context = ref<SymbolContext | null>(null)
const filtered = computed(() => filterSymbols(store.symbols, { query: query.value, language: language.value, type: type.value }))
const typeLabels: Record<string, string> = { CLASS: '类', INTERFACE: '接口', METHOD: '方法', FUNCTION: '函数' }

async function openSymbol(symbol: CodeSymbol) {
  selected.value = symbol
  drawerOpen.value = true
  contextLoading.value = true
  context.value = null
  try {
    context.value = await symbolsApi.context(symbol.id)
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    contextLoading.value = false
  }
}

onMounted(() => {
  const requested = typeof route.query.symbol === 'string' ? route.query.symbol : null
  const match = requested ? store.symbols.find((symbol) => symbol.id === requested) : null
  if (match) openSymbol(match)
})
</script>

<template>
  <div class="page-stack">
    <section class="filter-bar">
      <el-input v-model="query" placeholder="搜索名称或限定名" clearable class="search-input" />
      <el-select v-model="language" placeholder="语言" clearable><el-option label="Java" value="JAVA" /><el-option label="Python" value="PYTHON" /></el-select>
      <el-select v-model="type" placeholder="类型" clearable><el-option v-for="item in ['CLASS', 'INTERFACE', 'METHOD', 'FUNCTION']" :key="item" :label="typeLabels[item]" :value="item" /></el-select>
      <span class="result-count">共 {{ filtered.length }} 个 Symbol</span>
    </section>

    <section v-if="store.analysis" class="panel table-panel">
      <el-table :data="filtered" stripe height="calc(100vh - 245px)" empty-text="没有匹配的 Symbol" @row-click="openSymbol">
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="qualifiedName" label="限定名" min-width="300" show-overflow-tooltip />
        <el-table-column prop="type" label="类型" width="110"><template #default="scope"><el-tag size="small" effect="plain">{{ typeLabels[scope.row.type] || scope.row.type }}</el-tag></template></el-table-column>
        <el-table-column prop="language" label="语言" width="110"><template #default="scope">{{ scope.row.language === 'JAVA' ? 'Java' : 'Python' }}</template></el-table-column>
        <el-table-column prop="filePath" label="文件" min-width="180" show-overflow-tooltip />
        <el-table-column label="行号" width="100"><template #default="scope">{{ scope.row.startLine }}–{{ scope.row.endLine }}</template></el-table-column>
      </el-table>
    </section>
    <EmptyState v-else title="尚未分析仓库" description="分析仓库后即可浏览 Symbol 索引。" />

    <el-drawer v-model="drawerOpen" size="58%" :title="selected?.name || 'Symbol 详情'" destroy-on-close>
      <div v-if="selected" class="drawer-content" v-loading="contextLoading">
        <span class="eyebrow">Symbol</span><h2>{{ selected.qualifiedName }}</h2>
        <dl class="metadata-list compact"><div><dt>文件</dt><dd>{{ selected.filePath }}</dd></div><div><dt>行号</dt><dd>{{ selected.startLine }}–{{ selected.endLine }}</dd></div><div><dt>类型</dt><dd>{{ typeLabels[selected.type] }}</dd></div><div><dt>语言</dt><dd>{{ selected.language === 'JAVA' ? 'Java' : 'Python' }}</dd></div></dl>
        <template v-if="context">
          <section><div class="section-title-row"><h3>源码证据</h3><span class="file-label">{{ context.sourceSnippet?.filePath }}</span></div><CodeViewer v-if="context.sourceSnippet" :content="context.sourceSnippet.content" :start-line="context.sourceSnippet.requestedRange.startLine" :highlight-line="selected.startLine" /><p v-else>暂无源码</p></section>
          <div class="detail-grid context-grid">
            <article class="panel"><h3>调用方</h3><p v-if="!context.callers.length">暂无调用方</p><ul><li v-for="item in context.callers" :key="item.relation.id">{{ item.symbol.qualifiedName }}</li></ul></article>
            <article class="panel"><h3>被调用方</h3><p v-if="!context.callees.length">暂无被调用方</p><ul><li v-for="item in context.callees" :key="item.relation.id">{{ item.symbol.qualifiedName }}</li></ul></article>
            <article class="panel"><h3>引用</h3><p v-if="!context.references.length">暂无引用</p><ul><li v-for="item in context.references" :key="item.id">{{ item.filePath }}:{{ item.line }}</li></ul></article>
          </div>
        </template>
      </div>
    </el-drawer>
  </div>
</template>
