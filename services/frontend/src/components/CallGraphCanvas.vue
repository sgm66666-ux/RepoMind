<script setup lang="ts">
import cytoscape, { type Core, type EventObject } from 'cytoscape'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { CallGraphResult, CodeSymbol } from '../models'
import { toGraphElements } from '../utils/graph'

const props = withDefaults(defineProps<{ graph: CallGraphResult; height?: number }>(), { height: 520 })
const emit = defineEmits<{ select: [symbol: CodeSymbol] }>()
const container = ref<HTMLDivElement | null>(null)
let instance: Core | null = null
const graphLayout = {
  name: 'breadthfirst' as const,
  directed: true,
  padding: 40,
  spacingFactor: 1.25,
  transform: (_node: unknown, position: { x: number; y: number }) => ({ x: position.y * 1.1, y: position.x }),
}

function renderGraph() {
  if (!container.value) return
  instance?.destroy()
  instance = cytoscape({
    container: container.value,
    elements: toGraphElements(props.graph),
    style: [
      {
        selector: 'node',
        style: {
          'background-color': '#19243a',
          'border-color': '#294f87',
          'border-width': 1,
          color: '#17243b',
          label: 'data(label)',
          'font-family': 'JetBrains Mono, Consolas, monospace',
          'font-size': 11,
          'text-valign': 'center',
          'text-halign': 'center',
          width: '200px',
          height: '46px',
          shape: 'round-rectangle',
          'text-wrap': 'ellipsis',
          'text-max-width': '184px',
        },
      },
      { selector: 'node[kind = "method"]', style: { 'background-color': '#eaf1fb', 'border-color': '#7d9fc9' } },
      { selector: 'node[kind = "class"]', style: { 'background-color': '#e9eef4', 'border-color': '#6f7e91', 'shape': 'rectangle' } },
      { selector: 'node[unresolved]', style: { 'background-color': '#fff7e8', 'border-color': '#cf923c', 'border-style': 'dashed' } },
      {
        selector: 'edge',
        style: {
          width: 2,
          'line-color': '#557db4',
          'target-arrow-color': '#294f87',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
        },
      },
      { selector: 'edge.unresolved', style: { 'line-style': 'dashed', 'line-color': '#cf923c', 'target-arrow-color': '#cf923c' } },
      { selector: 'node:selected', style: { 'background-color': '#d8e8fb', 'border-color': '#234c81', 'border-width': 3 } },
    ],
    layout: graphLayout,
  })
  instance.on('tap', 'node', (event: EventObject) => {
    const symbol = event.target.data('symbol') as CodeSymbol | undefined
    if (symbol) emit('select', symbol)
  })
}

function fit() {
  instance?.fit(undefined, 35)
}

function zoom(factor: number) {
  if (!instance) return
  instance.zoom({ level: Math.max(instance.minZoom(), Math.min(instance.maxZoom(), instance.zoom() * factor)), renderedPosition: { x: instance.width() / 2, y: instance.height() / 2 } })
}

function reset() {
  instance?.layout(graphLayout).run()
  fit()
}

onMounted(renderGraph)
watch(() => props.graph, () => nextTick(renderGraph), { deep: true })
onBeforeUnmount(() => instance?.destroy())
</script>

<template>
  <div class="graph-panel">
    <div class="graph-toolbar">
      <span><i class="legend-line" /> 已解析调用</span>
      <span><i class="legend-line unresolved" /> 未解析候选</span>
      <span><i class="legend-node class" /> 类</span>
      <span><i class="legend-node method" /> 方法</span>
      <div class="toolbar-spacer" />
      <el-button size="small" aria-label="放大" @click="zoom(1.25)">＋</el-button>
      <el-button size="small" aria-label="缩小" @click="zoom(0.8)">－</el-button>
      <el-button size="small" @click="fit">适配</el-button>
      <el-button size="small" @click="reset">重置</el-button>
    </div>
    <div ref="container" class="graph-canvas" :style="{ height: `${height}px` }" />
  </div>
</template>
