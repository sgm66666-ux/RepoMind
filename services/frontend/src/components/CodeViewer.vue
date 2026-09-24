<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  content: string
  startLine?: number
  highlightLine?: number | null
}>(), {
  startLine: 1,
  highlightLine: null,
})

const lines = computed(() => props.content.split('\n'))
</script>

<template>
  <div class="code-viewer">
    <div
      v-for="(line, index) in lines"
      :key="index"
      class="code-line"
      :class="{ highlighted: startLine + index === highlightLine }"
    >
      <span class="line-number">{{ startLine + index }}</span>
      <code>{{ line || ' ' }}</code>
    </div>
  </div>
</template>
