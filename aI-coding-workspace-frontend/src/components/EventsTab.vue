<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import type { LangGraphEvent } from '@/api'

const store = useAppStore()
const scrollRef = ref<HTMLDivElement>()

// 过滤关键事件类型
const keyEventTypes = new Set([
  'on_chain_start',
  'on_chain_end',
  'on_chat_model_stream',
  'on_chat_model_start',
  'on_chat_model_end',
  'on_tool_start',
  'on_tool_end',
])

const filteredEvents = computed(() =>
  store.sseEvents.filter((e) => keyEventTypes.has(e.event)),
)

// 把事件渲染成可读的简短描述
function describe(e: LangGraphEvent): { label: string; detail?: string; level: string } {
  switch (e.event) {
    case 'on_chain_start':
      return { label: `节点启动: ${e.name}`, level: 'info' }
    case 'on_chain_end':
      return { label: `节点完成: ${e.name}`, level: 'success' }
    case 'on_chat_model_start':
      return { label: `模型调用: ${e.name}`, level: 'info' }
    case 'on_chat_model_stream': {
      const chunk = (e.data as { chunk?: { content?: string } })?.chunk
      const text = chunk?.content
      return { label: 'token', detail: typeof text === 'string' ? text : '', level: 'stream' }
    }
    case 'on_chat_model_end':
      return { label: `模型返回: ${e.name}`, level: 'success' }
    case 'on_tool_start':
      return { label: `工具调用: ${e.name}`, level: 'info' }
    case 'on_tool_end':
      return { label: `工具结束: ${e.name}`, level: 'success' }
    default:
      return { label: e.event, level: 'info' }
  }
}

watch(
  () => store.sseEvents.length,
  async () => {
    await nextTick()
    if (scrollRef.value) {
      scrollRef.value.scrollTop = scrollRef.value.scrollHeight
    }
  },
)

function levelColor(level: string): string {
  switch (level) {
    case 'success':
      return 'var(--ide-green)'
    case 'stream':
      return 'var(--ide-orange)'
    default:
      return 'var(--ide-accent)'
  }
}
</script>

<template>
  <div class="events-tab flex-col full-h">
    <div class="events-header">
      <div class="conn-status">
        <span
          class="dot"
          :class="{ on: store.sseConnected }"
        ></span>
        {{ store.sseConnected ? '已连接' : '未连接' }}
      </div>
      <span class="count">{{ filteredEvents.length }} 事件</span>
    </div>

    <div ref="scrollRef" class="events-list flex-1">
      <div v-if="filteredEvents.length === 0" class="empty">
        <el-icon :size="28" color="var(--ide-text-dim)"><DataLine /></el-icon>
        <p>Vibe Coding 执行时，这里会实时显示 LangGraph 事件流</p>
      </div>

      <div
        v-for="(e, idx) in filteredEvents"
        :key="idx"
        class="event-item"
      >
        <span class="event-dot" :style="{ background: levelColor(describe(e).level) }"></span>
        <span class="event-label">{{ describe(e).label }}</span>
        <span v-if="describe(e).detail" class="event-detail">{{ describe(e).detail }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.events-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.events-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--ide-border);
  font-size: 12px;
  color: var(--ide-text-dim);
}

.conn-status {
  display: flex;
  align-items: center;
  gap: 6px;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ide-text-dim);
}
.dot.on {
  background: var(--ide-green);
  box-shadow: 0 0 6px var(--ide-green);
}

.events-list {
  overflow-y: auto;
  padding: 8px;
  font-family: var(--ide-mono);
  font-size: 12px;
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--ide-text-dim);
  gap: 8px;
  text-align: center;
  padding: 20px;
}

.event-item {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 3px 4px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

.event-dot {
  flex-shrink: 0;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  position: relative;
  top: 2px;
}

.event-label {
  color: var(--ide-text);
  white-space: nowrap;
}

.event-detail {
  color: var(--ide-orange);
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
