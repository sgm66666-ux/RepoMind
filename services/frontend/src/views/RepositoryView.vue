<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import EmptyState from '../components/EmptyState.vue'
import StatCard from '../components/StatCard.vue'
import { useRepositoryStore } from '../stores/repository'
import { errorMessage } from '../utils/errors'

const store = useRepositoryStore()
const repositoryPath = ref(store.analysis?.repositoryPath || '')

async function analyze() {
  if (!repositoryPath.value.trim()) {
    ElMessage.warning('请输入仓库路径')
    return
  }
  try {
    await store.analyze(repositoryPath.value.trim())
    ElMessage.success('仓库分析完成')
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

async function analyzeDemo() {
  try {
    const result = await store.analyzeDemo()
    repositoryPath.value = result.repositoryPath
    ElMessage.success('演示仓库分析完成')
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}
</script>

<template>
  <div class="page-stack">
    <section class="panel analysis-form">
      <div><span class="eyebrow">仓库输入</span><h2>分析本地代码仓库</h2><p>输入后端服务可访问的绝对路径。RepoMind 以只读方式分析 Java 和 Python 代码。</p></div>
      <div class="path-input-row">
        <el-input v-model="repositoryPath" size="large" placeholder="输入后端可访问的仓库绝对路径" clearable @keyup.enter="analyze" />
        <el-button type="primary" size="large" :loading="store.loading" @click="analyze">开始分析</el-button>
        <el-button size="large" :disabled="store.loading" @click="analyzeDemo">分析演示仓库</el-button>
      </div>
      <div v-if="store.loading" class="analysis-status loading" role="status"><span class="loading-spinner" />正在扫描并建立代码索引，耗时取决于仓库规模…</div>
      <el-alert v-else-if="store.error" :title="`分析失败：${store.error}`" type="error" :closable="false" show-icon />
      <div v-else-if="store.analysis" class="analysis-status success" role="status"><span class="status-dot active" />分析完成 · {{ store.analysis.repositoryPath }}</div>
    </section>

    <template v-if="store.analysis">
      <div class="stats-grid">
        <StatCard label="代码文件" :value="store.analysis.sourceFileCount" />
        <StatCard label="Symbol 数量" :value="store.analysis.symbolCount" />
        <StatCard label="Relation 数量" :value="store.analysis.relationCount" />
        <StatCard label="Resolved Calls" :value="store.analysis.resolvedCallCount" />
        <StatCard label="未解析调用" :value="store.analysis.unresolvedCallCount" />
      </div>
      <section class="panel">
        <span class="eyebrow">语言分布</span>
        <h3>已索引的源码文件</h3>
        <div class="language-list">
          <div v-for="(count, language) in store.analysis.languageBreakdown" :key="language">
            <span>{{ language }}</span><strong>{{ count }}</strong>
          </div>
        </div>
      </section>
    </template>
    <EmptyState v-else title="尚未分析仓库" description="分析结果与语言分布将在这里显示。" />
  </div>
</template>
