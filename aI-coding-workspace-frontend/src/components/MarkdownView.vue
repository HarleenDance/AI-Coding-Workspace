<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps<{
  content: string
}>()

const html = computed(() => renderMarkdown(props.content))
</script>

<template>
  <div class="markdown-body" v-html="html"></div>
</template>

<style>
.markdown-body {
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 16px 0 8px;
  color: var(--ide-text-bright);
  font-weight: 600;
}
.markdown-body :deep(h1) {
  font-size: 20px;
}
.markdown-body :deep(h2) {
  font-size: 17px;
}
.markdown-body :deep(h3) {
  font-size: 15px;
}

.markdown-body :deep(p) {
  margin: 8px 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

.markdown-body :deep(code) {
  font-family: var(--ide-mono);
  font-size: 13px;
  background: var(--ide-bg-active);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--ide-orange);
}

.markdown-body :deep(.md-code-block) {
  background: #11111b;
  border: 1px solid var(--ide-border);
  border-radius: 6px;
  padding: 12px;
  overflow-x: auto;
  margin: 10px 0;
}

.markdown-body :deep(.md-code-block code) {
  background: none;
  padding: 0;
  color: var(--ide-text);
  font-size: 13px;
  line-height: 1.5;
}

.markdown-body :deep(a) {
  color: var(--ide-accent);
  text-decoration: none;
}
.markdown-body :deep(a:hover) {
  text-decoration: underline;
}

.markdown-body :deep(blockquote) {
  border-left: 3px solid var(--ide-accent);
  padding-left: 12px;
  margin: 8px 0;
  color: var(--ide-text-dim);
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid var(--ide-border);
  padding: 6px 12px;
}
.markdown-body :deep(th) {
  background: var(--ide-bg-active);
}
</style>
