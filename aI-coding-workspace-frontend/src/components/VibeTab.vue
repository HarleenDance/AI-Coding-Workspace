<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { api } from '@/api'
import MarkdownView from './MarkdownView.vue'
import CodeEditor from './CodeEditor.vue'

const store = useAppStore()
const requirement = ref('')
const feedback = ref('')
const showFeedback = ref(false)
const history = ref<Awaited<ReturnType<typeof api.getVibeHistory>>['tasks']>([])

async function loadHistory() {
  if (!store.projectId) return
  try {
    const res = await api.getVibeHistory(store.projectId)
    history.value = res.tasks
  } catch {
    history.value = []
  }
}

onMounted(loadHistory)
watch(() => store.projectId, loadHistory)
watch(() => store.vibePlan?.status, (s) => {
  if (s === 'completed' || s === 'rejected') loadHistory()
})

function start() {
  const r = requirement.value.trim()
  if (!r || store.vibeLoading) return
  requirement.value = ''
  store.startVibe(r)
}

function approve() {
  if (!store.vibePlan) return
  store.confirmVibe(true, feedback.value)
}

function reject() {
  if (!store.vibePlan) return
  store.confirmVibe(false, feedback.value)
}

function reset() {
  store.resetVibe()
  feedback.value = ''
  showFeedback.value = false
}

// 当进入审批阶段时，展开反馈框
watch(
  () => store.vibePlan?.status,
  (status) => {
    if (status === 'waiting_approval') {
      showFeedback.value = true
    }
  },
)
</script>

<template>
  <div class="vibe-tab flex-col full-h">
    <div class="vibe-content flex-1">
      <!-- 无任务：输入需求 -->
      <div v-if="!store.vibePlan" class="empty-state">
        <el-icon :size="32" color="var(--ide-purple)"><MagicStick /></el-icon>
        <p class="title">Vibe Coding</p>
        <p class="desc">描述你想要的改动，AI 会生成方案并等你确认后生成 diff</p>
      </div>

      <!-- 有任务 -->
      <div v-else class="vibe-flow">
        <!-- 状态条 -->
        <div class="status-bar">
          <el-tag
            :type="
              store.vibePlan.status === 'completed'
                ? 'success'
                : store.vibePlan.status === 'rejected'
                  ? 'info'
                  : 'warning'
            "
            size="small"
            effect="dark"
          >
            {{ store.vibePlan.status }}
          </el-tag>
          <span class="thread-id">{{ store.vibePlan.threadId.slice(0, 8) }}</span>
        </div>

        <!-- 方案展示 -->
        <div v-if="store.vibePlan.proposedPlan" class="plan-section">
          <div class="section-title">
            <el-icon><Document /></el-icon>
            修改方案
          </div>
          <MarkdownView :content="store.vibePlan.proposedPlan" />
        </div>

        <!-- diff 展示 -->
        <div v-if="store.vibePlan.diff" class="diff-section">
          <div class="section-title">
            <el-icon><Files /></el-icon>
            生成的 Diff
          </div>
          <div class="diff-viewer">
            <CodeEditor
              :original="''"
              :modified="store.vibePlan.diff"
              language="diff"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 历史记录 -->
    <div v-if="history.length > 0" class="history-section">
      <div class="section-title">
        <el-icon><Clock /></el-icon>
        历史任务 ({{ history.length }})
      </div>
      <div
        v-for="task in history.slice(0, 10)"
        :key="task.id"
        class="history-item"
      >
        <el-tag
          :type="task.status === 'completed' ? 'success' : task.status === 'rejected' ? 'info' : 'warning'"
          size="small"
          effect="dark"
        >
          {{ task.status }}
        </el-tag>
        <span class="history-text">{{ task.requirement }}</span>
        <span class="history-time">{{ task.created_at?.slice(5, 16).replace('T', ' ') }}</span>
      </div>
    </div>
    <!-- 底部操作区 -->
    <div class="vibe-actions">
      <!-- 输入需求 -->
      <template v-if="!store.vibePlan">
        <el-input
          v-model="requirement"
          type="textarea"
          :rows="3"
          :disabled="store.vibeLoading"
          placeholder="例如：给项目增加基于 JWT 的登录接口"
          resize="none"
        />
        <div class="action-row">
          <el-button
            type="primary"
            :loading="store.vibeLoading"
            @click="start"
          >
            <el-icon><Promotion /></el-icon>
            开始 Vibe Coding
          </el-button>
        </div>
      </template>

      <!-- 审批操作 -->
      <template v-else-if="store.vibePlan.status === 'waiting_approval'">
        <el-input
          v-if="showFeedback"
          v-model="feedback"
          type="textarea"
          :rows="2"
          placeholder="补充反馈（可选）"
          resize="none"
        />
        <div class="action-row">
          <el-button @click="reject" :loading="store.vibeLoading">
            <el-icon><Close /></el-icon>
            拒绝
          </el-button>
          <el-button type="primary" @click="approve" :loading="store.vibeLoading">
            <el-icon><Check /></el-icon>
            接受并生成 Diff
          </el-button>
        </div>
      </template>

      <!-- 完成后重置 -->
      <template v-else-if="['completed', 'rejected'].includes(store.vibePlan.status)">
        <div class="action-row">
          <el-button @click="reset">
            <el-icon><RefreshLeft /></el-icon>
            新建任务
          </el-button>
          <el-button
            v-if="store.vibePlan.status === 'completed' && store.vibePlan.diff"
            type="success"
            :loading="store.vibeLoading"
            @click="store.applyVibeDiff()"
          >
            <el-icon><Check /></el-icon>
            应用 Diff 到文件
          </el-button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.vibe-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.vibe-content {
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
  gap: 8px;
  text-align: center;
  padding: 20px;
}
.empty-state .title {
  font-size: 18px;
  color: var(--ide-text-bright);
  margin: 8px 0 0;
}
.empty-state .desc {
  font-size: 13px;
  max-width: 260px;
}

.vibe-flow {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}
.thread-id {
  font-family: var(--ide-mono);
  font-size: 12px;
  color: var(--ide-text-dim);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--ide-text-dim);
  margin-bottom: 8px;
  font-weight: 600;
}

.diff-section {
  margin-top: 8px;
}
.diff-viewer {
  height: 320px;
  border: 1px solid var(--ide-border);
  border-radius: 6px;
  overflow: hidden;
}

.vibe-actions {
  border-top: 1px solid var(--ide-border);
  padding: 8px;
  background: var(--ide-bg-elevated);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-section {
  border-top: 1px solid var(--ide-border);
  padding: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  font-size: 12px;
}

.history-text {
  flex: 1;
  color: var(--ide-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-time {
  color: var(--ide-text-dim);
  font-family: var(--ide-mono);
  font-size: 11px;
}

.action-row {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
