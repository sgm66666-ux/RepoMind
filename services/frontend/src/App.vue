<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useRepositoryStore } from './stores/repository'
import { useServicesStore } from './stores/services'

const route = useRoute()
const repository = useRepositoryStore()
const services = useServicesStore()
const title = computed(() => String(route.meta.title || '项目概览'))
const navigation = [
  { to: '/', label: '项目概览', icon: '▦' },
  { to: '/repository', label: '代码仓库', icon: '⌁' },
  { to: '/symbols', label: '符号索引', icon: '{}' },
  { to: '/call-graph', label: '调用关系图', icon: '◇' },
  { to: '/fault-localization', label: '故障定位', icon: '!' },
  { to: '/agent', label: '代码智能助手', icon: '›_' },
]
const gatewayLabel = computed(() => services.gateway === 'online' ? '正常' : services.gateway === 'offline' ? '离线' : '检测中')
const llmLabel = computed(() => services.llm === 'success' ? '本次调用成功' : services.llm === 'unconfigured' ? '未配置' : services.llm === 'failed' ? '调用失败' : '未验证')

onMounted(() => { void services.refresh() })
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand"><div class="brand-mark">R</div><div><strong>RepoMind</strong><span>代码分析工作台</span></div></div>
      <div class="nav-caption">工作空间</div>
      <nav class="navigation" aria-label="项目导航">
        <RouterLink v-for="item in navigation" :key="item.to" :to="item.to" class="nav-item" :aria-label="item.label">
          <span class="nav-icon" aria-hidden="true">{{ item.icon }}</span><span class="nav-label">{{ item.label }}</span>
        </RouterLink>
      </nav>
      <div class="sidebar-foot"><span class="status-dot" :class="{ active: repository.analysis }" />{{ repository.analysis ? '仓库已索引' : '等待分析仓库' }}</div>
    </aside>

    <section class="workspace">
      <header class="topbar">
        <div class="topbar-title"><span class="eyebrow">RepoMind / 工作空间</span><h1>{{ title }}</h1></div>
        <div class="topbar-right">
          <div class="topbar-status"><span class="status-dot" :class="{ active: services.gateway === 'online', error: services.gateway === 'offline' }" />网关 {{ gatewayLabel }}</div>
          <div class="topbar-status"><span class="status-dot" :class="{ active: services.llm === 'success', error: services.llm === 'failed' }" />LLM {{ llmLabel }}</div>
          <div class="repository-chip" :title="repository.analysis?.repositoryPath"><span class="status-dot" :class="{ active: repository.analysis }" /><span>{{ repository.analysis?.repositoryPath || '未分析仓库' }}</span></div>
        </div>
      </header>
      <main class="content"><RouterView /></main>
    </section>
  </div>
</template>
