<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import MenuBar from '@/components/MenuBar.vue'
import ActivityBar from '@/components/ActivityBar.vue'
import Sidebar from '@/components/Sidebar.vue'
import CodePanel from '@/components/CodePanel.vue'
import AIPanel from '@/components/AIPanel.vue'
import CommandPalette from '@/components/CommandPalette.vue'
import type { ActivityView } from '@/components/ActivityBar.vue'

const { t } = useI18n()

const store = useAppStore()

// 视图状态
const activityView = ref<ActivityView>('explorer')
const cmdVisible = ref(false)
const isMobile = ref(false)

function updateMobile() {
  isMobile.value = window.innerWidth <= 768
}

// 全局快捷键
function onGlobalKeydown(e: KeyboardEvent) {
  // Ctrl+P / Cmd+P: 文件搜索
  if ((e.ctrlKey || e.metaKey) && e.key === 'p' && !e.shiftKey) {
    e.preventDefault()
    cmdVisible.value = true
  }
  // Ctrl+Shift+P: 命令面板
  if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'P' || e.key === 'p')) {
    e.preventDefault()
    cmdVisible.value = true
  }
}

function handleCommandView(target: string) {
  if (target.startsWith('view-')) {
    activityView.value = target.replace('view-', '') as ActivityView
  }
}

// 移动端视图
type MobileView = 'files' | 'code' | 'ai'
const mobileView = ref<MobileView>('ai')

onMounted(() => {
  store.checkHealth()
  store.loadProjects()
  store.loadAgents()
  store.loadModels()
  updateMobile()
  window.addEventListener('resize', updateMobile)
  window.addEventListener('keydown', onGlobalKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateMobile)
  window.removeEventListener('keydown', onGlobalKeydown)
})
</script>

<template>
  <!-- 全局文件上传 input -->
  <input
    id="global-upload-input"
    type="file"
    accept=".zip"
    style="display: none"
    @change="(e) => { const t = e.target as HTMLInputElement; if (t.files?.length) store.uploadProject(t.files[0]); t.value = '' }"
  />

  <!-- 命令面板 -->
  <CommandPalette v-model:visible="cmdVisible" @command="handleCommandView" />

  <!-- 桌面端布局 -->
  <div v-if="!isMobile" class="layout desktop-layout">
    <!-- 顶部：菜单栏 + 标题栏 -->
    <div class="top-section">
      <MenuBar @view="handleCommandView" />
      <div class="title-bar">
        <div class="title-left">
          <el-icon class="logo" color="var(--ide-accent)" :size="16"><Cpu /></el-icon>
          <span class="app-name">AI Coding Workspace</span>
          <span v-if="store.currentProject" class="sep">—</span>
          <span v-if="store.currentProject" class="project-name">{{ store.currentProject.name }}</span>
        </div>
        <div class="title-center" v-if="store.projectId">
          <el-input
            v-model="store.searchQuery"
            size="small"
            :placeholder="t('titlebar.searchPlaceholder')"
            class="search-input"
            @keydown.enter="store.runSearch()"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
        <div class="title-right">
          <span class="db-status" :class="{ ok: store.healthOk, bad: store.healthOk === false }">
            <span class="status-dot"></span>
            {{ store.healthOk === null ? t('titlebar.checking') : store.healthOk ? t('titlebar.connected') : t('titlebar.offline') }}
          </span>
        </div>
      </div>
    </div>

    <!-- 主体：活动栏 + 侧栏 + 编辑器 + AI -->
    <div class="main-body">
      <ActivityBar v-model="activityView" />

      <!-- 侧栏内容根据 activityView 切换 -->
      <div v-show="activityView === 'explorer'" class="side-panel">
        <Sidebar />
      </div>
      <div v-show="activityView === 'search'" class="side-panel search-side">
        <div class="side-header">{{ t('search.title') }}</div>
        <div class="search-side-body">
          <el-input v-model="store.searchQuery" :placeholder="t('search.placeholder')" @keydown.enter="store.runSearch()">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-radio-group v-model="store.searchMode" size="small" style="margin-top: 8px">
            <el-radio-button value="keyword">{{ t('search.keyword') }}</el-radio-button>
            <el-radio-button value="semantic">{{ t('search.semantic') }}</el-radio-button>
          </el-radio-group>
          <div class="search-results-list">
            <div v-for="(r, i) in store.searchResults" :key="i" class="search-result-item" @click="store.openFile(r.file_path)">
              <span class="sr-file">{{ r.file_path }}</span>
              <span class="sr-score">{{ r.match_count || r.score.toFixed(2) }}</span>
            </div>
          </div>
        </div>
      </div>
      <div v-show="activityView === 'git'" class="side-panel">
        <div class="side-header">{{ t('git.title') }}</div>
        <div class="empty-side">
          <el-text size="small" type="info">{{ t('git.noChanges') }}</el-text>
        </div>
      </div>
      <div v-show="activityView === 'settings'" class="side-panel">
        <div class="side-header">{{ t('settings.title') }}</div>
        <div class="settings-body">
          <div class="setting-item">
            <span>{{ t('settings.database') }}</span>
            <el-tag :type="store.healthOk ? 'success' : 'danger'" size="small">
              {{ store.healthOk ? t('titlebar.connected') : t('titlebar.offline') }}
            </el-tag>
          </div>
          <div class="setting-item">
            <span>{{ t('settings.project') }}</span>
            <span class="setting-value">{{ store.currentProject?.name || t('settings.none') }}</span>
          </div>
          <div class="setting-item">
            <span>{{ t('settings.indexed') }}</span>
            <el-tag :type="store.currentProject?.is_indexed ? 'success' : 'info'" size="small">
              {{ store.currentProject?.is_indexed ? t('settings.yes') : t('settings.no') }}
            </el-tag>
          </div>
          <div class="setting-item">
            <span>{{ t('settings.language') }}</span>
            <el-select
              :model-value="$i18n.locale"
              size="small"
              style="width: 100px"
              @change="(v: string) => { $i18n.locale = v; localStorage.setItem('app-language', v) }"
            >
              <el-option label="中文" value="zh" />
              <el-option label="English" value="en" />
            </el-select>
          </div>
        </div>
      </div>

      <!-- 编辑器 -->
      <div class="editor-container">
        <CodePanel />
      </div>

      <!-- AI 面板 -->
      <div class="ai-container">
        <AIPanel />
      </div>
    </div>
  </div>

  <!-- 移动端布局 -->
  <div v-else class="layout mobile-layout">
    <div class="mobile-top">
      <div class="mobile-title">
        <el-icon color="var(--ide-accent)"><Cpu /></el-icon>
        <span>AI Workspace</span>
      </div>
    </div>
    <div class="mobile-content">
      <Sidebar v-show="mobileView === 'files'" class="mobile-view" />
      <CodePanel v-show="mobileView === 'code'" class="mobile-view" />
      <AIPanel v-show="mobileView === 'ai'" class="mobile-view" />
    </div>
    <nav class="mobile-nav">
      <button class="nav-btn" :class="{ active: mobileView === 'files' }" @click="mobileView = 'files'">
        <el-icon><Files /></el-icon><span>Files</span>
      </button>
      <button class="nav-btn" :class="{ active: mobileView === 'code' }" @click="mobileView = 'code'">
        <el-icon><Document /></el-icon><span>Code</span>
      </button>
      <button class="nav-btn" :class="{ active: mobileView === 'ai' }" @click="mobileView = 'ai'">
        <el-icon><ChatDotRound /></el-icon><span>AI</span>
      </button>
    </nav>
  </div>
</template>

<style scoped>
.layout {
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* ===== 桌面端 ===== */
.top-section {
  flex-shrink: 0;
}

.title-bar {
  display: flex;
  align-items: center;
  height: 36px;
  padding: 0 12px;
  background: var(--ide-bg);
  border-bottom: 1px solid var(--ide-border);
  gap: 12px;
}

.title-left {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.app-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--ide-text-bright);
  white-space: nowrap;
}

.sep {
  color: var(--ide-text-dim);
  font-size: 12px;
}

.project-name {
  font-size: 12px;
  color: var(--ide-text-dim);
}

.title-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.search-input {
  max-width: 400px;
  width: 100%;
}

.title-right {
  flex-shrink: 0;
}

.db-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--ide-text-dim);
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--ide-text-dim);
}
.db-status.ok .status-dot { background: var(--ide-green); box-shadow: 0 0 6px var(--ide-green); }
.db-status.bad .status-dot { background: var(--ide-red); box-shadow: 0 0 6px var(--ide-red); }

.main-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.side-panel {
  flex-shrink: 0;
  border-right: 1px solid var(--ide-border);
  overflow: hidden;
}

.side-header {
  height: 30px;
  display: flex;
  align-items: center;
  padding: 0 14px;
  font-size: 11px;
  font-weight: 600;
  color: var(--ide-text-dim);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.search-side-body {
  padding: 8px 12px;
  width: 260px;
}

.search-results-list {
  margin-top: 8px;
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

.search-result-item {
  display: flex;
  justify-content: space-between;
  padding: 4px 6px;
  cursor: pointer;
  border-radius: 4px;
  font-size: 12px;
}
.search-result-item:hover { background: var(--ide-bg-hover); }
.sr-file { color: var(--ide-accent); font-family: var(--ide-mono); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sr-score { color: var(--ide-text-dim); flex-shrink: 0; }

.empty-side {
  padding: 40px 20px;
  text-align: center;
}

.settings-body {
  padding: 8px 12px;
  width: 260px;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  font-size: 12px;
  border-bottom: 1px solid var(--ide-border);
}
.setting-value { color: var(--ide-text-dim); }

.editor-container {
  flex: 1;
  overflow: hidden;
  min-width: 0;
}

.ai-container {
  width: 420px;
  flex-shrink: 0;
  border-left: 1px solid var(--ide-border);
  overflow: hidden;
}

/* ===== 移动端 ===== */
.mobile-top {
  height: 40px;
  display: flex;
  align-items: center;
  padding: 0 12px;
  background: var(--ide-bg-elevated);
  border-bottom: 1px solid var(--ide-border);
}

.mobile-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
}

.mobile-content {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.mobile-view {
  position: absolute;
  inset: 0;
}

.mobile-nav {
  display: flex;
  height: 56px;
  background: var(--ide-bg-elevated);
  border-top: 1px solid var(--ide-border);
  flex-shrink: 0;
}

.nav-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  background: none;
  border: none;
  color: var(--ide-text-dim);
  cursor: pointer;
  font-size: 11px;
}
.nav-btn .el-icon { font-size: 20px; }
.nav-btn.active { color: var(--ide-accent); }
</style>
