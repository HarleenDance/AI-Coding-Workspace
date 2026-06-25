<script setup lang="ts">
import { ref, computed } from 'vue'
import http from '@/api/http'
import { ElMessage } from 'element-plus'

// ===== Token 管理 =====
const token = ref(localStorage.getItem('yuque_token') || '')
const tokenInput = ref('')
const showTokenInput = ref(!token.value)
const userInfo = ref<any>(null)
const loading = ref(false)

function saveToken() {
  if (!tokenInput.value.trim()) {
    ElMessage.warning('请输入 Token')
    return
  }
  token.value = tokenInput.value.trim()
  localStorage.setItem('yuque_token', token.value)
  showTokenInput.value = false
  loadUser()
}

function clearToken() {
  token.value = ''
  tokenInput.value = ''
  userInfo.value = null
  repos.value = []
  docs.value = []
  localStorage.removeItem('yuque_token')
  showTokenInput.value = true
}

// ===== 数据 =====
const repos = ref<any[]>([])
const currentRepo = ref<any>(null)
const docs = ref<any[]>([])
const currentDoc = ref<any>(null)
const docContent = ref('')
const viewMode = ref<'list' | 'doc'>('list')

async function loadUser() {
  loading.value = true
  try {
    const res = await http.post('/yuque/user', { token: token.value })
    userInfo.value = res.data
    await loadRepos()
  } catch (e: any) {
    ElMessage.error('Token 无效或网络错误')
    clearToken()
  } finally {
    loading.value = false
  }
}

async function loadRepos() {
  loading.value = true
  try {
    const res = await http.post('/yuque/repos', { token: token.value })
    repos.value = res.data || []
  } catch {
    ElMessage.error('获取知识库失败')
  } finally {
    loading.value = false
  }
}

async function openRepo(repo: any) {
  currentRepo.value = repo
  loading.value = true
  try {
    const res = await http.post(`/yuque/repos/${repo.namespace}/docs`, { token: token.value })
    docs.value = res.data || []
    viewMode.value = 'list'
  } catch {
    ElMessage.error('获取文档列表失败')
  } finally {
    loading.value = false
  }
}

async function openDoc(doc: any) {
  loading.value = true
  try {
    const res = await http.post(`/yuque/repos/${currentRepo.value.namespace}/docs/${doc.slug}`, { token: token.value })
    currentDoc.value = res.data
    docContent.value = res.data?.body || res.data?.body_lake || ''
    viewMode.value = 'doc'
  } catch {
    ElMessage.error('获取文档失败')
  } finally {
    loading.value = false
  }
}

function backToList() {
  viewMode.value = 'list'
  currentDoc.value = null
}

function backToRepos() {
  currentRepo.value = null
  docs.value = []
  viewMode.value = 'list'
}

// 导入到项目
async function importDoc() {
  if (!currentDoc.value) return
  const fileName = (currentDoc.value.title || 'untitled').replace(/[\\/:*?"<>|]/g, '_') + '.md'
  const content = `# ${currentDoc.value.title}\n\n来源：语雀 ${currentRepo.value?.name}\n\n${docContent.value}`
  // 触发事件让父组件处理导入
  emit('import', { fileName, content })
  ElMessage.success(`已导入：${fileName}`)
}

const emit = defineEmits<{
  import: [{ fileName: string; content: string }]
}>()

// 初始化
if (token.value) {
  loadUser()
}
</script>

<template>
  <div class="yuque-panel">
    <!-- Header -->
    <div class="panel-header">
      <el-icon color="var(--ide-accent)"><Reading /></el-icon>
      <span>语雀文档</span>
      <span v-if="userInfo" class="user-name">{{ userInfo.name }}</span>
      <el-button v-if="token" text size="small" @click="clearToken" style="margin-left: auto">
        <el-icon><SwitchButton /></el-icon>
      </el-button>
    </div>

    <!-- Token 输入 -->
    <div v-if="showTokenInput" class="token-input-area">
      <el-alert type="info" :closable="false" show-icon>
        <template #title>如何获取 Token？</template>
        <div style="font-size: 12px; line-height: 1.6">
          1. 打开 <a href="https://www.yuque.com/settings/tokens" target="_blank">语雀设置页</a><br>
          2. 点击「新建 Token」<br>
          3. 勾选 <code>repo_read</code> 权限<br>
          4. 复制 Token 粘贴到下方
        </div>
      </el-alert>
      <el-input
        v-model="tokenInput"
        type="password"
        show-password
        placeholder="粘贴语雀 Personal Token"
        style="margin-top: 12px"
        @keydown.enter="saveToken"
      />
      <el-button type="primary" style="width: 100%; margin-top: 8px" @click="saveToken">
        连接语雀
      </el-button>
    </div>

    <!-- 加载中 -->
    <div v-else-if="loading" class="loading-area">
      <el-icon class="is-loading" :size="24"><Loading /></el-icon>
      <span>加载中...</span>
    </div>

    <!-- 知识库列表 -->
    <div v-else-if="!currentRepo" class="repo-list">
      <div class="section-title">我的知识库 ({{ repos.length }})</div>
      <div
        v-for="repo in repos"
        :key="repo.id"
        class="repo-item"
        @click="openRepo(repo)"
      >
        <el-icon><Notebook /></el-icon>
        <div class="repo-info">
          <div class="repo-name">{{ repo.name }}</div>
          <div class="repo-desc">{{ repo.description || repo.namespace }}</div>
        </div>
      </div>
      <div v-if="repos.length === 0" class="empty">暂无知识库</div>
    </div>

    <!-- 文档列表 -->
    <div v-else-if="viewMode === 'list'" class="doc-list">
      <div class="breadcrumb" @click="backToRepos">
        <el-icon><ArrowLeft /></el-icon>
        <span>{{ currentRepo.name }}</span>
      </div>
      <div class="section-title">文档 ({{ docs.length }})</div>
      <div
        v-for="doc in docs"
        :key="doc.id"
        class="doc-item"
        @click="openDoc(doc)"
      >
        <el-icon><Document /></el-icon>
        <span class="doc-title">{{ doc.title }}</span>
      </div>
      <div v-if="docs.length === 0" class="empty">暂无文档</div>
    </div>

    <!-- 文档详情 -->
    <div v-else class="doc-detail">
      <div class="breadcrumb">
        <el-icon @click="backToList"><ArrowLeft /></el-icon>
        <span>{{ currentDoc?.title }}</span>
        <el-button text size="small" style="margin-left: auto" @click="importDoc">
          <el-icon><Download /></el-icon>
          导入到项目
        </el-button>
      </div>
      <div class="doc-content" v-html="docContent" v-if="docContent.includes('<')"></div>
      <div class="doc-content" v-else>
        <pre style="white-space: pre-wrap; font-family: inherit">{{ docContent }}</pre>
      </div>
    </div>
  </div>
</template>

<style scoped>
.yuque-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 12px;
  height: 32px;
  font-size: 13px;
  font-weight: 500;
  color: var(--ide-text);
  border-bottom: 1px solid var(--ide-border);
  flex-shrink: 0;
}

.user-name {
  margin-left: 4px;
  font-size: 11px;
  color: var(--ide-text-dim);
}

.token-input-area {
  padding: 12px;
  overflow-y: auto;
}

.loading-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px;
  color: var(--ide-text-dim);
}

.repo-list, .doc-list, .doc-detail {
  flex: 1;
  overflow-y: auto;
}

.section-title {
  padding: 8px 12px 4px;
  font-size: 11px;
  color: var(--ide-text-dim);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.repo-item, .doc-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  cursor: pointer;
  color: var(--ide-text);
  font-size: 13px;
}

.repo-item:hover, .doc-item:hover {
  background: var(--ide-bg-hover);
}

.repo-info {
  flex: 1;
  min-width: 0;
}

.repo-name {
  font-size: 13px;
  color: var(--ide-text);
}

.repo-desc {
  font-size: 11px;
  color: var(--ide-text-dim);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  font-size: 13px;
  color: var(--ide-text);
  border-bottom: 1px solid var(--ide-border);
  cursor: pointer;
}

.doc-content {
  padding: 16px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--ide-text);
}

.empty {
  padding: 40px 12px;
  text-align: center;
  color: var(--ide-text-dim);
  font-size: 12px;
}

a {
  color: var(--ide-accent);
}
</style>
