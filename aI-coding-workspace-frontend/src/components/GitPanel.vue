<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useAppStore } from '@/stores/app'
import { api } from '@/api'

interface GitFile {
  path: string
  staged_status: string
  working_status: string
  is_staged: boolean
  is_untracked: boolean
}

interface GitStatus {
  initialized: boolean
  branch: string
  ahead_behind: { ahead: number; behind: number }
  files: GitFile[]
}

interface GitCommit {
  hash: string
  short_hash: string
  author: string
  email: string
  timestamp: number
  subject: string
}

const store = useAppStore()
const status = ref<GitStatus | null>(null)
const loading = ref(false)
const selectedDiff = ref('')
const selectedPath = ref('')
const commitMessage = ref('')
const commitDescription = ref('')
const committing = ref(false)
const commits = ref<GitCommit[]>([])
const showHistory = ref(false)
const selectedFiles = ref<Set<string>>(new Set())

async function loadStatus() {
  if (!store.projectId) return
  loading.value = true
  try {
    const res = await httpGet<GitStatus>(`/projects/${store.projectId}/git/status`)
    status.value = res
  } catch {
    status.value = null
  } finally {
    loading.value = false
  }
}

async function loadDiff(path?: string) {
  if (!store.projectId) return
  try {
    const res = await httpGet<{ diff: string }>(
      `/projects/${store.projectId}/git/diff`,
      { staged: false, path },
    )
    selectedDiff.value = res.diff
    selectedPath.value = path || ''
  } catch {
    selectedDiff.value = ''
  }
}

async function loadStagedDiff() {
  if (!store.projectId) return
  try {
    const res = await httpGet<{ diff: string }>(
      `/projects/${store.projectId}/git/diff`,
      { staged: true },
    )
    selectedDiff.value = res.diff
    selectedPath.value = '__staged__'
  } catch {
    selectedDiff.value = ''
  }
}

async function stageFile(path: string) {
  await httpPost(`/projects/${store.projectId}/git/stage`, { paths: [path] })
  await loadStatus()
}

async function stageAll() {
  await httpPost(`/projects/${store.projectId}/git/stage`, { paths: [] })
  await loadStatus()
  ElMessage.success('已暂存全部')
}

async function unstageFile(path: string) {
  await httpPost(`/projects/${store.projectId}/git/unstage`, { paths: [path] })
  await loadStatus()
}

async function unstageAll() {
  await httpPost(`/projects/${store.projectId}/git/unstage`, { paths: [] })
  await loadStatus()
}

async function commit() {
  if (!commitMessage.value.trim()) {
    ElMessage.warning('请输入提交信息')
    return
  }
  committing.value = true
  try {
    await httpPost(`/projects/${store.projectId}/git/commit`, {
      message: commitMessage.value,
      description: commitDescription.value || undefined,
    })
    ElMessage.success('提交成功')
    commitMessage.value = ''
    commitDescription.value = ''
    await loadStatus()
    await loadHistory()
  } finally {
    committing.value = false
  }
}

async function loadHistory() {
  if (!store.projectId) {
    commits.value = []
    return
  }
  try {
    const res = await httpGet<{ commits: GitCommit[] }>(
      `/projects/${store.projectId}/git/log`,
      { limit: 30 },
    )
    commits.value = res.commits
  } catch {
    commits.value = []
  }
}

async function initRepo() {
  await httpPost(`/projects/${store.projectId}/git/init`, {})
  ElMessage.success('已初始化 git 仓库')
  await loadStatus()
}

function toggleSelect(path: string) {
  if (selectedFiles.value.has(path)) {
    selectedFiles.value.delete(path)
  } else {
    selectedFiles.value.add(path)
  }
}

function statusLabel(file: GitFile): string {
  if (file.is_untracked) return 'U'
  if (file.staged_status === 'modified') return 'M'
  if (file.staged_status === 'added') return 'A'
  if (file.staged_status === 'deleted') return 'D'
  return file.staged_status ? file.staged_status[0].toUpperCase() : '?'
}

function statusColor(file: GitFile): string {
  if (file.is_untracked) return 'var(--ide-text-dim)'
  if (file.staged_status === 'modified') return 'var(--ide-yellow)'
  if (file.staged_status === 'added') return 'var(--ide-green)'
  if (file.staged_status === 'deleted') return 'var(--ide-red)'
  return 'var(--ide-text-dim)'
}

function formatTime(ts: number): string {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  const now = new Date()
  const diff = (now.getTime() - d.getTime()) / 1000
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)} 天前`
  return d.toLocaleDateString('zh-CN')
}

// 简易 http 包装（带 query）
async function httpGet<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const query = params
    ? '?' + Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null)
        .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
        .join('&')
    : ''
  return api.httpGet<T>(url + query)
}

async function httpPost(url: string, body: unknown): Promise<void> {
  await api.httpPost(url, body)
}

onMounted(() => {
  loadStatus()
  loadHistory()
})

watch(() => store.projectId, () => {
  loadStatus()
  loadHistory()
})
</script>

<template>
  <div class="git-panel flex-col full-h">
    <div class="git-header">
      <div class="header-row">
        <el-icon color="var(--ide-accent)"><Connection /></el-icon>
        <span class="header-title">源代码管理</span>
        <el-button
          v-if="status?.initialized"
          text
          size="small"
          @click="loadStatus"
          :loading="loading"
        >
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
      <div v-if="status?.initialized" class="branch-info">
        <el-icon><Position /></el-icon>
        <span>{{ status.branch || 'HEAD' }}</span>
        <el-tag
          v-if="status.ahead_behind.ahead"
          size="small"
          type="warning"
          effect="dark"
        >
          ↑{{ status.ahead_behind.ahead }}
        </el-tag>
        <el-tag
          v-if="status.ahead_behind.behind"
          size="small"
          type="info"
          effect="dark"
        >
          ↓{{ status.ahead_behind.behind }}
        </el-tag>
      </div>
    </div>

    <!-- 未初始化 -->
    <div v-if="status && !status.initialized" class="empty-state">
      <el-icon :size="32" color="var(--ide-text-dim)"><Connection /></el-icon>
      <p>该项目还不是 Git 仓库</p>
      <el-button type="primary" size="small" @click="initRepo">
        <el-icon><Plus /></el-icon>
        初始化仓库
      </el-button>
    </div>

    <!-- Git 操作界面 -->
    <div v-else-if="status?.initialized" class="git-content flex-1">
      <!-- 提交区 -->
      <div class="commit-section">
        <el-input
          v-model="commitMessage"
          placeholder="提交信息（必填）"
          size="small"
          maxlength="72"
        />
        <el-input
          v-model="commitDescription"
          placeholder="描述（可选）"
          type="textarea"
          :rows="2"
          size="small"
          style="margin-top: 6px"
        />
        <el-button
          type="primary"
          size="small"
          style="margin-top: 6px; width: 100%"
          :loading="committing"
          :disabled="!commitMessage.trim()"
          @click="commit"
        >
          <el-icon><Check /></el-icon>
          提交
        </el-button>
      </div>

      <!-- 暂存区 -->
      <div class="section">
        <div class="section-head">
          <span class="section-title">
            暂存的更改
            <span v-if="status.files.filter(f => f.is_staged).length" class="count">
              {{ status.files.filter(f => f.is_staged).length }}
            </span>
          </span>
          <el-button
            v-if="status.files.some(f => f.is_staged)"
            text
            size="small"
            @click="unstageAll"
          >
            全部取消
          </el-button>
        </div>
        <div
          v-for="file in status.files.filter(f => f.is_staged)"
          :key="file.path"
          class="file-item"
          :class="{ active: selectedPath === file.path }"
          @click="loadDiff(file.path)"
        >
          <span class="file-status" :style="{ color: statusColor(file) }">
            {{ statusLabel(file) }}
          </span>
          <span class="file-name">{{ file.path.split('/').pop() }}</span>
          <span class="file-path">{{ file.path }}</span>
          <div class="file-actions" @click.stop>
            <el-button text size="small" @click="unstageFile(file.path)">
              <el-icon><Minus /></el-icon>
            </el-button>
          </div>
        </div>
        <div v-if="!status.files.some(f => f.is_staged)" class="empty-hint">
          暂无暂存的更改
        </div>
      </div>

      <!-- 工作区 -->
      <div class="section">
        <div class="section-head">
          <span class="section-title">
            更改
            <span v-if="status.files.filter(f => !f.is_staged).length" class="count">
              {{ status.files.filter(f => !f.is_staged).length }}
            </span>
          </span>
          <el-button
            v-if="status.files.some(f => !f.is_staged)"
            text
            size="small"
            @click="stageAll"
          >
            全部暂存
          </el-button>
        </div>
        <div
          v-for="file in status.files.filter(f => !f.is_staged)"
          :key="file.path"
          class="file-item"
          :class="{ active: selectedPath === file.path }"
          @click="loadDiff(file.path)"
        >
          <span class="file-status" :style="{ color: statusColor(file) }">
            {{ statusLabel(file) }}
          </span>
          <span class="file-name">{{ file.path.split('/').pop() }}</span>
          <span class="file-path">{{ file.path }}</span>
          <div class="file-actions" @click.stop>
            <el-button text size="small" @click="stageFile(file.path)">
              <el-icon><Plus /></el-icon>
            </el-button>
          </div>
        </div>
        <div v-if="!status.files.some(f => !f.is_staged)" class="empty-hint">
          工作区干净
        </div>
      </div>

      <!-- Diff 预览 -->
      <div v-if="selectedDiff" class="diff-preview">
        <div class="section-head">
          <span class="section-title">
            <el-icon><Document /></el-icon>
            {{ selectedPath === '__staged__' ? '已暂存' : selectedPath }}
          </span>
        </div>
        <pre class="diff-content">{{ selectedDiff }}</pre>
      </div>

      <!-- 历史记录 -->
      <div class="section">
        <div class="section-head" @click="showHistory = !showHistory" style="cursor: pointer">
          <span class="section-title">
            <el-icon><Clock /></el-icon>
            提交历史
            <span v-if="commits.length" class="count">{{ commits.length }}</span>
            <el-icon class="arrow" :class="{ open: showHistory }"><ArrowDown /></el-icon>
          </span>
        </div>
        <div v-if="showHistory" class="history-list">
          <div
            v-for="c in commits.slice(0, 20)"
            :key="c.hash"
            class="commit-item"
          >
            <div class="commit-hash">{{ c.short_hash }}</div>
            <div class="commit-info">
              <div class="commit-subject">{{ c.subject }}</div>
              <div class="commit-meta">
                {{ c.author }} · {{ formatTime(c.timestamp) }}
              </div>
            </div>
          </div>
          <div v-if="!commits.length" class="empty-hint">暂无提交</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.git-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 280px;
  background: var(--ide-bg-elevated);
}

.git-header {
  padding: 8px 12px;
  border-bottom: 1px solid var(--ide-border);
}

.header-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.header-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--ide-text);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  flex: 1;
}

.branch-info {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  font-size: 12px;
  color: var(--ide-text-dim);
  font-family: var(--ide-mono);
}

.git-content {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--ide-text-dim);
  gap: 12px;
  text-align: center;
  padding: 20px;
}

.commit-section {
  padding: 8px 12px;
  border-bottom: 1px solid var(--ide-border);
}

.section {
  border-bottom: 1px solid var(--ide-border);
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: var(--ide-bg-darker);
  user-select: none;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--ide-text-dim);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.count {
  background: var(--ide-bg-active);
  color: var(--ide-text);
  padding: 0 6px;
  border-radius: 8px;
  font-size: 10px;
  min-width: 16px;
  text-align: center;
}

.arrow {
  transition: transform 0.2s;
  margin-left: auto;
}
.arrow.open {
  transform: rotate(180deg);
}

.file-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  font-size: 12px;
  cursor: pointer;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}
.file-item:hover {
  background: var(--ide-bg-hover);
}
.file-item.active {
  background: var(--ide-bg-active);
}

.file-status {
  width: 14px;
  text-align: center;
  font-weight: 700;
  font-family: var(--ide-mono);
  flex-shrink: 0;
}

.file-name {
  color: var(--ide-text);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-path {
  color: var(--ide-text-dim);
  font-size: 11px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-actions {
  opacity: 0;
  transition: opacity 0.15s;
  flex-shrink: 0;
}

.file-item:hover .file-actions {
  opacity: 1;
}

.empty-hint {
  padding: 8px 12px;
  font-size: 11px;
  color: var(--ide-text-dim);
  text-align: center;
}

.diff-preview {
  border-bottom: 1px solid var(--ide-border);
}

.diff-content {
  font-family: var(--ide-mono);
  font-size: 11px;
  padding: 8px 12px;
  margin: 0;
  max-height: 200px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--ide-text);
}

.history-list {
  padding: 4px 0;
}

.commit-item {
  display: flex;
  gap: 8px;
  padding: 6px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

.commit-hash {
  font-family: var(--ide-mono);
  font-size: 11px;
  color: var(--ide-accent);
  flex-shrink: 0;
  padding-top: 1px;
}

.commit-info {
  flex: 1;
  min-width: 0;
}

.commit-subject {
  font-size: 12px;
  color: var(--ide-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.commit-meta {
  font-size: 10px;
  color: var(--ide-text-dim);
  margin-top: 2px;
}
</style>
