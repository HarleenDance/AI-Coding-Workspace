<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import type { LangGraphEvent } from '@/api'

const store = useAppStore()
const scrollRef = ref<HTMLDivElement>()

// 工作流节点定义（与后端 workflow.py 对齐）
const WORKFLOW_NODES = [
  { id: 'router_agent', label: 'Router', icon: '🔀', desc: '意图路由' },
  { id: 'planner_agent', label: 'Planner', icon: '📋', desc: '方案规划' },
  { id: 'human_approval_node', label: 'Approval', icon: '✋', desc: '人工确认' },
  { id: 'coder_agent', label: 'Coder', icon: '💻', desc: '代码生成' },
  { id: 'qa_agent', label: 'QA', icon: '🔍', desc: '质量审查' },
] as const

// 节点状态：idle / running / done
interface NodeState {
  id: string
  status: 'idle' | 'running' | 'done'
  startTime?: number
  endTime?: number
}

const nodeStates = ref<NodeState[]>(
  WORKFLOW_NODES.map((n) => ({ id: n.id, status: 'idle' })),
)

// 从 SSE 事件更新节点状态
function updateNodeStates() {
  const events = store.sseEvents
  const newStates: NodeState[] = WORKFLOW_NODES.map((n) => ({ id: n.id, status: 'idle' }))

  for (const e of events) {
    if (e.event === 'on_chain_start' && e.name) {
      const node = newStates.find((n) => n.id === e.name)
      if (node && node.status === 'idle') {
        node.status = 'running'
        node.startTime = Date.now()
      }
    } else if (e.event === 'on_chain_end' && e.name) {
      const node = newStates.find((n) => n.id === e.name)
      if (node) {
        node.status = 'done'
        node.endTime = Date.now()
      }
    }
  }

  nodeStates.value = newStates
}

// 统计信息
const stats = computed(() => {
  const events = store.sseEvents
  const modelCalls = events.filter((e) => e.event === 'on_chat_model_start').length
  const toolCalls = events.filter((e) => e.event === 'on_tool_start').length
  const tokenEvents = events.filter((e) => e.event === 'on_chat_model_stream')
  const tokens = tokenEvents.reduce((sum, e) => {
    const chunk = (e.data as { chunk?: { content?: string } })?.chunk
    const text = chunk?.content
    return sum + (typeof text === 'string' ? text.length : 0)
  }, 0)

  const done = nodeStates.value.find((n) => n.status === 'done')
  const running = nodeStates.value.find((n) => n.status === 'running')
  const firstStart = nodeStates.value.find((n) => n.startTime)?.startTime
  const lastEnd = [...nodeStates.value].reverse().find((n) => n.endTime)?.endTime

  return {
    totalEvents: events.length,
    modelCalls,
    toolCalls,
    tokens,
    duration: firstStart && lastEnd ? ((lastEnd - firstStart) / 1000).toFixed(1) + 's' : running ? '进行中' : '-',
  }
})

// 当前活动节点
const activeNode = computed(() => nodeStates.value.find((n) => n.status === 'running'))

// 按节点分组的事件时间线
interface TimelineGroup {
  nodeId: string
  label: string
  icon: string
  events: LangGraphEvent[]
  status: 'idle' | 'running' | 'done'
}

const timelineGroups = computed<TimelineGroup[]>(() => {
  const events = store.sseEvents
  const groups = new Map<string, LangGraphEvent[]>()

  // 关键事件类型
  const keyEventTypes = new Set([
    'on_chain_start',
    'on_chain_end',
    'on_chat_model_stream',
    'on_chat_model_start',
    'on_chat_model_end',
    'on_tool_start',
    'on_tool_end',
  ])

  let currentNode = '__start__'
  groups.set(currentNode, [])

  for (const e of events) {
    if (!keyEventTypes.has(e.event)) continue

    // 节点切换
    if (e.event === 'on_chain_start' && e.name && WORKFLOW_NODES.some((n) => n.id === e.name)) {
      currentNode = e.name
      if (!groups.has(currentNode)) groups.set(currentNode, [])
    }

    groups.get(currentNode)?.push(e)
  }

  return WORKFLOW_NODES.map((node) => ({
    nodeId: node.id,
    label: node.label,
    icon: node.icon,
    events: groups.get(node.id) || [],
    status: nodeStates.value.find((n) => n.id === node.id)?.status || 'idle',
  })).filter((g) => g.events.length > 0 || g.status !== 'idle')
})

// 把事件渲染成可读的简短描述
function describe(e: LangGraphEvent): { label: string; detail?: string; level: string } {
  switch (e.event) {
    case 'on_chain_start':
      return { label: `节点启动`, level: 'info' }
    case 'on_chain_end':
      return { label: `节点完成`, level: 'success' }
    case 'on_chat_model_start':
      return { label: `模型调用`, level: 'info' }
    case 'on_chat_model_stream': {
      const chunk = (e.data as { chunk?: { content?: string } })?.chunk
      const text = chunk?.content
      return { label: '', detail: typeof text === 'string' ? text : '', level: 'stream' }
    }
    case 'on_chat_model_end':
      return { label: `模型返回`, level: 'success' }
    case 'on_tool_start':
      return { label: `工具调用`, level: 'info' }
    case 'on_tool_end':
      return { label: `工具结束`, level: 'success' }
    default:
      return { label: e.event, level: 'info' }
  }
}

function levelColor(level: string): string {
  switch (level) {
    case 'success': return 'var(--ide-green)'
    case 'stream': return 'var(--ide-orange)'
    default: return 'var(--ide-accent)'
  }
}

function nodeDuration(nodeId: string): string {
  const node = nodeStates.value.find((n) => n.id === nodeId)
  if (!node?.startTime) return ''
  const end = node.endTime || Date.now()
  return ((end - node.startTime) / 1000).toFixed(1) + 's'
}

// 重置：当 SSE 重连或新任务时清空节点状态
watch(() => store.sseEvents.length, async () => {
  updateNodeStates()
  await nextTick()
  if (scrollRef.value) {
    scrollRef.value.scrollTop = scrollRef.value.scrollHeight
  }
}, { flush: 'post' })

watch(() => store.sseConnected, (connected) => {
  if (!connected) {
    // 保持最后状态，不清空
  } else {
    // 新连接，重置节点状态
    nodeStates.value = WORKFLOW_NODES.map((n) => ({ id: n.id, status: 'idle' }))
  }
})

// 初始化时同步一次
updateNodeStates()
</script>

<template>
  <div class="events-tab flex-col full-h">
    <!-- 头部：连接状态 + 统计 -->
    <div class="events-header">
      <div class="header-row">
        <div class="conn-status">
          <span class="dot" :class="{ on: store.sseConnected }"></span>
          {{ store.sseConnected ? '已连接' : '未连接' }}
        </div>
        <div class="stats-bar">
          <span class="stat" title="事件总数">
            <el-icon><DataLine /></el-icon>
            {{ stats.totalEvents }}
          </span>
          <span class="stat" title="模型调用次数">
            <el-icon><Cpu /></el-icon>
            {{ stats.modelCalls }}
          </span>
          <span class="stat" title="生成字符数">
            <el-icon><EditPen /></el-icon>
            {{ stats.tokens }}
          </span>
          <span class="stat" title="耗时">
            <el-icon><Timer /></el-icon>
            {{ stats.duration }}
          </span>
        </div>
      </div>
    </div>

    <!-- 工作流节点流程图 -->
    <div class="workflow-graph">
      <div
        v-for="(node, idx) in WORKFLOW_NODES"
        :key="node.id"
        class="wf-node-wrap"
      >
        <div
          class="wf-node"
          :class="nodeStates.find(n => n.id === node.id)?.status"
        >
          <span class="wf-icon">{{ node.icon }}</span>
          <div class="wf-info">
            <span class="wf-label">{{ node.label }}</span>
            <span class="wf-desc">{{ node.desc }}</span>
          </div>
          <span
            v-if="nodeDuration(node.id)"
            class="wf-duration"
          >
            {{ nodeDuration(node.id) }}
          </span>
        </div>
        <!-- 连接线 -->
        <div
          v-if="idx < WORKFLOW_NODES.length - 1"
          class="wf-arrow"
          :class="{
            active: nodeStates.find(n => n.id === node.id)?.status === 'done'
          }"
        >
          ↓
        </div>
      </div>
    </div>

    <!-- 当前活动节点高亮 -->
    <div v-if="activeNode" class="active-banner">
      <el-icon class="is-loading"><Loading /></el-icon>
      正在执行: {{ activeNode.id }}
    </div>

    <!-- 时间线 -->
    <div ref="scrollRef" class="events-list flex-1">
      <div v-if="timelineGroups.length === 0" class="empty">
        <el-icon :size="28" color="var(--ide-text-dim)"><DataLine /></el-icon>
        <p>Vibe Coding 执行时，这里会实时显示 Agent 工作流</p>
      </div>

      <div
        v-for="group in timelineGroups"
        :key="group.nodeId"
        class="timeline-group"
      >
        <div class="group-header">
          <span class="group-icon">{{ group.icon }}</span>
          <span class="group-label">{{ group.label }}</span>
          <span
            class="group-status"
            :class="group.status"
          >
            {{ group.status === 'done' ? '完成' : group.status === 'running' ? '执行中' : '待执行' }}
          </span>
          <span v-if="nodeDuration(group.nodeId)" class="group-duration">
            {{ nodeDuration(group.nodeId) }}
          </span>
        </div>

        <div class="group-events">
          <div
            v-for="(e, idx) in group.events.slice(-30)"
            :key="idx"
            class="event-item"
          >
            <span
              class="event-dot"
              :style="{ background: levelColor(describe(e).level) }"
            ></span>
            <span v-if="describe(e).label" class="event-label">{{ describe(e).label }}</span>
            <span v-if="describe(e).detail" class="event-detail">{{ describe(e).detail }}</span>
          </div>
        </div>
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
  padding: 6px 10px;
  border-bottom: 1px solid var(--ide-border);
  font-size: 11px;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.conn-status {
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--ide-text-dim);
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--ide-text-dim);
}
.dot.on {
  background: var(--ide-green);
  box-shadow: 0 0 6px var(--ide-green);
}

.stats-bar {
  display: flex;
  gap: 10px;
}

.stat {
  display: flex;
  align-items: center;
  gap: 3px;
  color: var(--ide-text-dim);
  font-family: var(--ide-mono);
}

.stat .el-icon {
  font-size: 12px;
}

/* 工作流流程图 */
.workflow-graph {
  padding: 8px 10px;
  border-bottom: 1px solid var(--ide-border);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.wf-node-wrap {
  display: flex;
  flex-direction: column;
  align-items: stretch;
}

.wf-node {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 6px;
  background: var(--ide-bg);
  border: 1px solid var(--ide-border);
  transition: all 0.2s;
}

.wf-node.idle {
  opacity: 0.4;
}

.wf-node.running {
  border-color: var(--ide-accent);
  background: rgba(var(--ide-accent-rgb, 137, 180, 250), 0.08);
  box-shadow: 0 0 8px rgba(137, 180, 250, 0.2);
  animation: pulse 1.5s ease-in-out infinite;
}

.wf-node.done {
  border-color: var(--ide-green);
  background: rgba(var(--ide-green-rgb, 166, 227, 161), 0.06);
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 6px rgba(137, 180, 250, 0.2); }
  50% { box-shadow: 0 0 12px rgba(137, 180, 250, 0.4); }
}

.wf-icon {
  font-size: 14px;
}

.wf-info {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.wf-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--ide-text);
}

.wf-desc {
  font-size: 10px;
  color: var(--ide-text-dim);
}

.wf-duration {
  font-size: 10px;
  color: var(--ide-text-dim);
  font-family: var(--ide-mono);
  flex-shrink: 0;
}

.wf-arrow {
  text-align: center;
  color: var(--ide-text-dim);
  font-size: 10px;
  line-height: 1;
  padding: 1px 0;
  opacity: 0.4;
  transition: opacity 0.2s, color 0.2s;
}

.wf-arrow.active {
  opacity: 1;
  color: var(--ide-green);
}

/* 活动横幅 */
.active-banner {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(137, 180, 250, 0.08);
  border-bottom: 1px solid var(--ide-border);
  font-size: 11px;
  color: var(--ide-accent);
  font-family: var(--ide-mono);
}

/* 时间线 */
.events-list {
  overflow-y: auto;
  padding: 6px;
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
  font-size: 12px;
}

.timeline-group {
  margin-bottom: 8px;
  border: 1px solid var(--ide-border);
  border-radius: 6px;
  overflow: hidden;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: var(--ide-bg-darker);
  font-size: 11px;
}

.group-icon {
  font-size: 13px;
}

.group-label {
  font-weight: 600;
  color: var(--ide-text);
  flex: 1;
}

.group-status {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 8px;
}

.group-status.done {
  background: rgba(166, 227, 161, 0.15);
  color: var(--ide-green);
}

.group-status.running {
  background: rgba(137, 180, 250, 0.15);
  color: var(--ide-accent);
}

.group-status.idle {
  color: var(--ide-text-dim);
}

.group-duration {
  font-size: 10px;
  color: var(--ide-text-dim);
  font-family: var(--ide-mono);
}

.group-events {
  padding: 4px 8px;
  font-family: var(--ide-mono);
  font-size: 11px;
}

.event-item {
  display: flex;
  align-items: baseline;
  gap: 5px;
  padding: 2px 0;
}

.event-dot {
  flex-shrink: 0;
  width: 5px;
  height: 5px;
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
