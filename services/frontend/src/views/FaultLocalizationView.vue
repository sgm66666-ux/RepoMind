<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { demoApi } from '../api/demo'
import { faultApi } from '../api/fault'
import EmptyState from '../components/EmptyState.vue'
import FaultResultPanel from '../components/FaultResultPanel.vue'
import type { FaultLocalizationResult } from '../models'
import { errorMessage } from '../utils/errors'

const stackTrace = ref('')
const loading = ref(false)
const result = ref<FaultLocalizationResult | null>(null)

async function loadDemo() {
  try {
    stackTrace.value = (await demoApi.getOrderDemo()).stackTrace
    ElMessage.success('已加载真实的 order-demo Stack Trace')
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

async function analyze() {
  if (!stackTrace.value.trim()) {
    ElMessage.warning('请先输入 Stack Trace')
    return
  }
  loading.value = true
  result.value = null
  try {
    result.value = await faultApi.analyze(stackTrace.value)
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-stack">
    <section class="panel fault-input">
      <div class="section-title-row"><div><span class="eyebrow">运行时证据</span><h2>输入 Stack Trace</h2><p>定位结果基于当前已索引仓库，不会把规则推断标为 LLM 结论。</p></div><el-button @click="loadDemo">加载演示堆栈</el-button></div>
      <el-input v-model="stackTrace" type="textarea" :rows="8" resize="vertical" placeholder="粘贴 Java 或 Python Stack Trace…" />
      <div class="form-actions"><el-button type="primary" size="large" :loading="loading" @click="analyze">开始定位</el-button></div>
    </section>
    <FaultResultPanel v-if="result" :result="result" />
    <EmptyState v-else title="暂无定位结果" description="输入堆栈后，RepoMind 将关联 Stack Trace、Symbol、调用关系和源码证据。" />
  </div>
</template>
