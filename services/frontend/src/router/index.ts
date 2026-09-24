import { createRouter, createWebHistory } from 'vue-router'
import OverviewView from '../views/OverviewView.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'overview', component: OverviewView, meta: { title: '项目概览' } },
    { path: '/repository', name: 'repository', component: () => import('../views/RepositoryView.vue'), meta: { title: '代码仓库' } },
    { path: '/symbols', name: 'symbols', component: () => import('../views/SymbolsView.vue'), meta: { title: '符号索引' } },
    { path: '/call-graph', name: 'call-graph', component: () => import('../views/CallGraphView.vue'), meta: { title: '调用关系图' } },
    { path: '/fault-localization', name: 'fault', component: () => import('../views/FaultLocalizationView.vue'), meta: { title: '故障定位' } },
    { path: '/agent', name: 'agent', component: () => import('../views/AgentView.vue'), meta: { title: '代码智能助手' } },
  ],
})
