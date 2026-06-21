<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAppStore } from '@/stores/app'
import type { FileTreeNode } from '@/api'

const props = withDefaults(defineProps<{
  name: string
  node: FileTreeNode
  depth?: number
}>(), {
  depth: 0,
})

const store = useAppStore()
const expanded = ref(props.depth < 1)

function toggle() {
  expanded.value = !expanded.value
}

function open() {
  if (props.node._path) {
    store.openFile(props.node._path)
  }
}

const entries = computed(() => {
  const children = props.node._children || {}
  return Object.entries(children).sort(([a], [b]) => {
    // 目录在前
    const aIsDir = children[a]._type === 'dir'
    const bIsDir = children[b]._type === 'dir'
    if (aIsDir !== bIsDir) return aIsDir ? -1 : 1
    return a.localeCompare(b)
  })
})
</script>

<template>
  <div>
    <!-- 目录节点 -->
    <div
      v-if="node._type === 'dir'"
      class="tree-item dir"
      :style="{ paddingLeft: `${depth * 14 + 8}px` }"
      @click.stop="toggle"
    >
      <span class="arrow" :class="{ expanded }">&#9656;</span>
      <span class="icon">{{ expanded ? '\u{1F4C2}' : '\u{1F4C1}' }}</span>
      <span class="label">{{ name }}</span>
    </div>
    <template v-if="node._type === 'dir' && expanded">
      <FileTreeNodeItem
        v-for="[childName, childNode] in entries"
        :key="childName"
        :name="childName"
        :node="childNode"
        :depth="depth + 1"
      />
    </template>

    <!-- 文件节点 -->
    <div
      v-if="node._type === 'file'"
      class="tree-item file"
      :class="{ active: store.currentFile?.path === node._path }"
      :style="{ paddingLeft: `${depth * 14 + 26}px` }"
      @click="open"
    >
      <span class="icon">{{ '\u{1F4C4}' }}</span>
      <span class="label">{{ name }}</span>
    </div>
  </div>
</template>

<style scoped>
.tree-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  cursor: pointer;
  font-size: 13px;
  color: var(--ide-text);
  user-select: none;
  white-space: nowrap;
}
.tree-item:hover {
  background: var(--ide-bg-hover);
}
.tree-item.active {
  background: var(--ide-bg-active);
  color: var(--ide-accent);
}
.tree-item.dir {
  font-weight: 500;
}
.arrow {
  display: inline-block;
  font-size: 10px;
  color: var(--ide-text-dim);
  transition: transform 0.15s;
  width: 12px;
}
.arrow.expanded {
  transform: rotate(90deg);
}
.icon {
  font-size: 14px;
  flex-shrink: 0;
}
.label {
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
