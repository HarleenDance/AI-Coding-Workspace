<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { api } from '@/api'
import MarkdownView from './MarkdownView.vue'
import CodeEditor from './CodeEditor.vue'

const store = useAppStore()
const requirement = ref('')
const feedback = ref('')
const showFeedback = ref(false)
const history = ref<Awaited<ReturnType<typeof api.getVibeHistory>>['tasks']>([])

const harnessTagType = computed(() =>
  store.vibePlan?.harness?.passed ? 'success' : 'danger',
)
const reviewTagType = computed(() =>
  store.vibePlan?.review?.passed ? 'success' : 'danger',
)

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
watch(() => store.vibePlan?.status, (status) => {
  if (status === 'completed' || status === 'rejected') loadHistory()
})

function start() {
  const text = requirement.value.trim()
  if (!text || store.vibeLoading) return
  requirement.value = ''
  store.startVibe(text)
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

watch(
  () => store.vibePlan?.status,
  (status) => {
    if (status === 'waiting_approval') showFeedback.value = true
  },
)
</script>

<template>
  <div class="vibe-tab flex-col full-h">
    <div class="vibe-content flex-1">
      <div v-if="!store.vibePlan" class="empty-state">
        <el-icon :size="32" color="var(--ide-purple)"><MagicStick /></el-icon>
        <p class="title">SDD AI Coding</p>
        <p class="desc">描述需求后，Agent 会生成规范方案、等待确认、产出 Diff，并自动执行 Harness 测试和代码审查。</p>
      </div>

      <div v-else class="vibe-flow">
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
          <span v-if="store.vibePlan.retryCount" class="retry">重试 {{ store.vibePlan.retryCount }} 次</span>
        </div>

        <div v-if="store.vibePlan.proposedPlan" class="panel">
          <div class="section-title">
            <el-icon><Document /></el-icon>
            SDD 实施方案
          </div>
          <MarkdownView :content="store.vibePlan.proposedPlan" />
        </div>

        <div v-if="store.vibePlan.harness" class="panel">
          <div class="section-title">
            <el-icon><CircleCheck /></el-icon>
            Harness 测试
            <el-tag :type="harnessTagType" size="small">
              {{ store.vibePlan.harness.passed ? '通过' : '失败' }}
            </el-tag>
          </div>
          <p class="summary">{{ store.vibePlan.harness.summary || store.vibePlan.harness.error }}</p>
          <div v-for="run in store.vibePlan.harness.runs" :key="run.command" class="run-item">
            <div class="run-head">
              <code>{{ run.command }}</code>
              <el-tag :type="run.passed ? 'success' : 'danger'" size="small">
                {{ run.return_code }}
              </el-tag>
            </div>
            <pre v-if="run.stderr || run.stdout">{{ run.stderr || run.stdout }}</pre>
          </div>
        </div>

        <div v-if="store.vibePlan.review" class="panel">
          <div class="section-title">
            <el-icon><Search /></el-icon>
            Reviewer 审查
            <el-tag :type="reviewTagType" size="small">
              {{ store.vibePlan.review.passed ? '通过' : '需修复' }}
            </el-tag>
          </div>
          <p class="summary">{{ store.vibePlan.review.summary }}</p>
          <ul v-if="store.vibePlan.review.findings?.length" class="findings">
            <li v-for="item in store.vibePlan.review.findings" :key="`${item.dimension}-${item.message}`">
              <strong>{{ item.severity }}</strong>
              <span>{{ item.dimension }}</span>
              {{ item.message }}
            </li>
          </ul>
        </div>

        <div v-if="store.vibePlan.diff" class="panel diff-section">
          <div class="section-title">
            <el-icon><Files /></el-icon>
            生成 Diff
          </div>
          <div class="diff-viewer">
            <CodeEditor :original="''" :modified="store.vibePlan.diff" language="diff" />
          </div>
        </div>
      </div>
    </div>

    <div v-if="history.length > 0" class="history-section">
      <div class="section-title">
        <el-icon><Clock /></el-icon>
        历史任务 ({{ history.length }})
      </div>
      <div v-for="task in history.slice(0, 10)" :key="task.id" class="history-item">
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

    <div class="vibe-actions">
      <template v-if="!store.vibePlan">
        <el-input
          v-model="requirement"
          type="textarea"
          :rows="3"
          :disabled="store.vibeLoading"
          placeholder="例如：给项目增加基于 JWT 的登录接口，并补充单元测试"
          resize="none"
        />
        <div class="action-row">
          <el-button type="primary" :loading="store.vibeLoading" @click="start">
            <el-icon><Promotion /></el-icon>
            开始 SDD Coding
          </el-button>
        </div>
      </template>

      <template v-else-if="store.vibePlan.status === 'waiting_approval'">
        <el-input
          v-if="showFeedback"
          v-model="feedback"
          type="textarea"
          :rows="2"
          placeholder="补充约束或调整意见，可留空"
          resize="none"
        />
        <div class="action-row">
          <el-button :loading="store.vibeLoading" @click="reject">
            <el-icon><Close /></el-icon>
            拒绝
          </el-button>
          <el-button type="primary" :loading="store.vibeLoading" @click="approve">
            <el-icon><Check /></el-icon>
            接受并生成 Diff
          </el-button>
        </div>
      </template>

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
            应用 Diff
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
  max-width: 320px;
  line-height: 1.6;
}

.vibe-flow {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-bar,
.section-title,
.run-head,
.history-item,
.action-row {
  display: flex;
  align-items: center;
}

.status-bar {
  gap: 8px;
  padding: 4px 0;
}

.thread-id,
.history-time {
  font-family: var(--ide-mono);
  color: var(--ide-text-dim);
}

.thread-id,
.retry {
  font-size: 12px;
}

.panel {
  border: 1px solid var(--ide-border);
  border-radius: 6px;
  padding: 10px;
  background: var(--ide-bg-elevated);
}

.section-title {
  gap: 6px;
  font-size: 13px;
  color: var(--ide-text-dim);
  margin-bottom: 8px;
  font-weight: 600;
}

.summary {
  margin: 0;
  color: var(--ide-text);
  font-size: 13px;
  line-height: 1.5;
}

.run-item {
  margin-top: 8px;
}

.run-head {
  justify-content: space-between;
  gap: 8px;
}

.run-head code {
  font-family: var(--ide-mono);
  font-size: 12px;
  color: var(--ide-text-bright);
}

pre {
  max-height: 180px;
  overflow: auto;
  margin: 8px 0 0;
  padding: 8px;
  border-radius: 4px;
  background: var(--ide-bg);
  color: var(--ide-text);
  font-family: var(--ide-mono);
  font-size: 12px;
  white-space: pre-wrap;
}

.findings {
  margin: 8px 0 0;
  padding-left: 18px;
  color: var(--ide-text);
  font-size: 13px;
}

.findings span {
  margin: 0 6px;
  color: var(--ide-text-dim);
}

.diff-viewer {
  height: 320px;
  border: 1px solid var(--ide-border);
  border-radius: 6px;
  overflow: hidden;
}

.vibe-actions,
.history-section {
  border-top: 1px solid var(--ide-border);
  padding: 8px;
  background: var(--ide-bg-elevated);
}

.vibe-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-section {
  max-height: 200px;
  overflow-y: auto;
}

.history-item {
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
  font-size: 11px;
}

.action-row {
  justify-content: flex-end;
  gap: 8px;
}
</style>
