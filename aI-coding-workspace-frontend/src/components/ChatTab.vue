<script setup lang="ts">
import { nextTick, ref, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import MarkdownView from './MarkdownView.vue'
import AgentSelector from './AgentSelector.vue'
import ModelSelector from './ModelSelector.vue'

const store = useAppStore()
const input = ref('')
const scrollRef = ref<HTMLDivElement>()
const showAgentMention = ref(false)
const mentionFilter = ref('')

const filteredAgents = computed(() =>
  store.agents.filter((a) =>
    a.name.toLowerCase().includes(mentionFilter.value.toLowerCase()),
  ),
)

function onInput(e: Event) {
  const target = e.target as HTMLTextAreaElement
  const val = target.value
  const cursorPos = target.selectionStart
  // 检测 @ 触发
  const beforeCursor = val.slice(0, cursorPos)
  const atMatch = beforeCursor.match(/@(\w*)$/)
  if (atMatch) {
    showAgentMention.value = true
    mentionFilter.value = atMatch[1]
  } else {
    showAgentMention.value = false
  }
}

function mentionAgent(name: string, id: string) {
  // 替换 @xxx 为 @name
  const val = input.value
  const cursorPos = (document.querySelector('.chat-input textarea') as HTMLTextAreaElement)?.selectionStart || val.length
  const before = val.slice(0, cursorPos).replace(/@(\w*)$/, '')
  const after = val.slice(cursorPos)
  input.value = `${before}@${name} ${after}`
  showAgentMention.value = false
  store.currentAgentId = id
}

async function send() {
  let q = input.value.trim()
  if (!q || store.chatLoading) return
  input.value = ''
  showAgentMention.value = false
  await store.sendChat(q)
  await nextTick()
  scrollToBottom()
}

function scrollToBottom() {
  if (scrollRef.value) {
    scrollRef.value.scrollTop = scrollRef.value.scrollHeight
  }
}
</script>

<template>
  <div class="chat-tab">
    <!-- 模型选择器 -->
    <ModelSelector />

    <!-- 智能体选择器 -->
    <AgentSelector />

    <!-- 消息列表 -->
    <div ref="scrollRef" class="messages">
      <div v-if="store.chatMessages.length === 0" class="empty-state">
        <el-icon :size="32" color="var(--ide-text-dim)"><ChatDotRound /></el-icon>
        <p>向 AI 提问关于代码库的问题</p>
        <div class="tips">
          <span>输入 <kbd>@</kbd> 切换智能体</span>
        </div>
      </div>

      <div
        v-for="msg in store.chatMessages"
        :key="msg.id"
        class="msg-item"
        :class="msg.role"
      >
        <div class="msg-avatar">
          <span v-if="msg.role === 'user'">🧑</span>
          <span v-else>{{ store.currentAgent?.avatar || '🤖' }}</span>
        </div>
        <div class="msg-content">
          <div class="msg-role">
            {{ msg.role === 'user' ? '你' : (store.currentAgent?.name || 'AI') }}
          </div>
          <div v-if="msg.loading" class="msg-loading">
            <el-icon class="is-loading"><Loading /></el-icon>
            思考中...
          </div>
          <MarkdownView v-else :content="msg.content" />
        </div>
      </div>
    </div>

    <!-- 上下文预览（右键追加的代码） -->
    <div v-if="store.chatContext" class="context-preview">
      <div class="context-header">
        <el-icon><Document /></el-icon>
        <span>已附加代码上下文</span>
        <el-button text size="small" @click="store.clearChatContext()">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
      <pre class="context-snippet">{{ store.chatContext.slice(0, 200) }}{{ store.chatContext.length > 200 ? '...' : '' }}</pre>
    </div>

    <!-- 输入区 -->
    <div class="input-area">
      <div class="input-wrap">
        <el-input
          v-model="input"
          class="chat-input"
          type="textarea"
          :rows="3"
          :disabled="store.chatLoading"
          placeholder="问一个问题... 输入 @ 切换智能体"
          resize="none"
          @input="onInput"
          @keydown.enter.exact.prevent="send"
        />
        <!-- @ 提及浮层 -->
        <div v-if="showAgentMention" class="mention-popup">
          <div class="mention-title">选择智能体</div>
          <div
            v-for="agent in filteredAgents"
            :key="agent.id"
            class="mention-item"
            @mousedown.prevent="mentionAgent(agent.name, agent.id)"
          >
            <span class="mention-avatar">{{ agent.avatar }}</span>
            <div class="mention-info">
              <span class="mention-name">{{ agent.name }}</span>
              <span class="mention-desc">{{ agent.description }}</span>
            </div>
          </div>
          <div v-if="filteredAgents.length === 0" class="mention-empty">
            没有匹配的智能体
          </div>
        </div>
      </div>
      <div class="input-actions">
        <el-button text size="small" @click="store.clearChat()" :disabled="store.chatLoading">
          清空
        </el-button>
        <el-button
          type="primary"
          size="small"
          :loading="store.chatLoading"
          @click="send"
        >
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--ide-text-dim);
  gap: 12px;
}

.tips {
  font-size: 12px;
  color: var(--ide-text-dim);
}

kbd {
  background: var(--ide-bg-elevated);
  border: 1px solid var(--ide-border);
  border-radius: 3px;
  padding: 1px 6px;
  font-size: 11px;
  font-family: var(--ide-mono);
}

.msg-item {
  display: flex;
  gap: 10px;
  padding: 12px 8px;
  border-bottom: 1px solid var(--ide-border);
}

.msg-avatar {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  background: var(--ide-bg-active);
  font-size: 16px;
}

.msg-content {
  flex: 1;
  min-width: 0;
  overflow-x: auto;
}

.msg-role {
  font-size: 12px;
  color: var(--ide-text-dim);
  margin-bottom: 4px;
}

.msg-loading {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--ide-text-dim);
  font-size: 13px;
}

.context-preview {
  margin: 0 8px;
  padding: 8px;
  border: 1px solid var(--ide-border);
  border-radius: 6px;
  background: var(--ide-bg);
  font-size: 12px;
}

.context-header {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--ide-accent);
  font-weight: 600;
  margin-bottom: 4px;
}

.context-header .el-button {
  margin-left: auto;
}

.context-snippet {
  font-family: var(--ide-mono);
  font-size: 11px;
  color: var(--ide-text-dim);
  margin: 0;
  max-height: 60px;
  overflow: hidden;
}

.input-area {
  border-top: 1px solid var(--ide-border);
  padding: 8px;
  background: var(--ide-bg-elevated);
}

.input-wrap {
  position: relative;
}

.mention-popup {
  position: absolute;
  bottom: 100%;
  left: 0;
  right: 0;
  background: var(--ide-bg-elevated);
  border: 1px solid var(--ide-border-light);
  border-radius: 6px;
  box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.3);
  padding: 4px;
  max-height: 240px;
  overflow-y: auto;
  z-index: 100;
  margin-bottom: 4px;
}

.mention-title {
  font-size: 11px;
  color: var(--ide-text-dim);
  padding: 4px 8px;
}

.mention-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.mention-item:hover {
  background: var(--ide-accent);
}

.mention-item:hover .mention-name,
.mention-item:hover .mention-desc {
  color: #1e1e2e;
}

.mention-avatar {
  font-size: 18px;
}

.mention-info {
  display: flex;
  flex-direction: column;
}

.mention-name {
  font-size: 13px;
  color: var(--ide-text);
}

.mention-desc {
  font-size: 11px;
  color: var(--ide-text-dim);
}

.mention-empty {
  padding: 12px;
  text-align: center;
  color: var(--ide-text-dim);
  font-size: 12px;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
}
</style>
