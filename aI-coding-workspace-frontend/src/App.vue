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
import TerminalPanel from '@/components/TerminalPanel.vue'
import YuquePanel from '@/components/YuquePanel.vue'
import BrowserPanel from '@/components/BrowserPanel.vue'
import GitPanel from '@/components/GitPanel.vue'
import type { ActivityView } from '@/components/ActivityBar.vue'

const { t } = useI18n()

const store = useAppStore()

// 视图状态
const activityView = ref<ActivityView>('explorer')
const cmdVisible = ref(false)
const isMobile = ref(false)
const terminalVisible = ref(false)
const terminalHeight = ref(240)
const editorMode = ref<'code' | 'browser'>('code')
const browserVisible = ref(false)

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
  // Ctrl+`: 切换终端
  if ((e.ctrlKey || e.metaKey) && e.key === '`') {
    e.preventDefault()
    terminalVisible.value = !terminalVisible.value
  }
}

function handleCommandView(target: string) {
  if (target.startsWith('view-')) {
    activityView.value = target.replace('view-', '') as ActivityView
  }
}

// 语雀文档导入到项目
async function handleYuqueImport(doc: { fileName: string; content: string }) {
  // 把导入的文档以虚拟文件方式打开（不实际写库，只在前端 Tab 展示）
  if (store.projectId) {
    try {
      // 尝试写入项目文件系统
      await store.importExternalFile(doc.fileName, doc.content)
    } catch {
      // 降级：直接作为新 Tab 打开
      store.openVirtualFile(`语雀导入/${doc.fileName}`, doc.content, 'markdown')
    }
  } else {
    store.openVirtualFile(`语雀导入/${doc.fileName}`, doc.content, 'markdown')
  }
}

// 终端面板拖拽调整高度
function startResize(e: MouseEvent) {
  e.preventDefault()
  const startY = e.clientY
  const startHeight = terminalHeight.value

  const onMove = (ev: MouseEvent) => {
    const delta = startY - ev.clientY
    const newHeight = Math.max(100, Math.min(window.innerHeight - 200, startHeight + delta))
    terminalHeight.value = newHeight
  }
  const onUp = () => {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    document.body.style.cursor = ''
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
  document.body.style.cursor = 'ns-resize'
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
      <ActivityBar v-model="activityView" @toggle-terminal="terminalVisible = !terminalVisible" />

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
        <GitPanel />
      </div>
      <div v-show="activityView === 'yuque'" class="side-panel">
        <YuquePanel @import="handleYuqueImport" />
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

      <!-- 编辑器 + 浏览器 + 终端 -->
      <div class="editor-container">
        <!-- 编辑器/浏览器切换 Tab -->
        <div class="editor-switcher">
          <div
            class="switcher-tab"
            :class="{ active: editorMode === 'code' }"
            @click="editorMode = 'code'"
          >
            <el-icon><Document /></el-icon>
            <span>编辑器</span>
          </div>
          <div
            class="switcher-tab"
            :class="{ active: editorMode === 'browser' }"
            @click="editorMode = 'browser'"
          >
            <el-icon><Monitor /></el-icon>
            <span>浏览器</span>
          </div>
        </div>

        <div class="editor-main" v-show="editorMode === 'code'">
          <CodePanel />
        </div>
        <div class="editor-main" v-show="editorMode === 'browser'">
          <BrowserPanel v-model:visible="browserVisible" :visible="true" />
        </div>

        <!-- 可拖拽分隔条 -->
        <div
          v-if="terminalVisible && editorMode === 'code'"
          class="terminal-resizer"
          @mousedown="startResize"
        ></div>
        <!-- 终端面板 -->
        <div
          v-if="terminalVisible && editorMode === 'code'"
          class="terminal-wrapper"
          :style="{ height: terminalHeight + 'px' }"
        >
          <TerminalPanel v-model:visible="terminalVisible" />
        </div>
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
  background: var(--ide-bg-darker);
}

.title-bar {
  display: flex;
  align-items: center;
  height: 32px;
  padding: 0 12px;
  background: var(--ide-bg-darker);
  gap: 10px;
}

.title-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.app-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--ide-text-bright);
  white-space: nowrap;
  letter-spacing: 0.3px;
}

.sep {
  color: var(--ide-text-dim);
  font-size: 12px;
  opacity: 0.5;
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
.search-input :deep(.el-input__wrapper) {
  background: var(--ide-bg-elevated);
  border-radius: 6px;
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
  background: var(--ide-bg);
}

.side-panel {
  flex-shrink: 0;
  border-right: 1px solid var(--ide-border);
  overflow: hidden;
  background: var(--ide-bg-elevated);
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
  display: flex;
  flex-direction: column;
}

/* 编辑器/浏览器切换 Tab */
.editor-switcher {
  display: flex;
  background: var(--ide-bg-darker);
  border-bottom: 1px solid var(--ide-border);
  flex-shrink: 0;
  height: 30px;
  padding: 0 4px;
  align-items: center;
  gap: 2px;
}

.switcher-tab {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  height: 24px;
  font-size: 12px;
  color: var(--ide-text-dim);
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.15s;
}

.switcher-tab:hover {
  color: var(--ide-text);
  background: rgba(255, 255, 255, 0.05);
}

.switcher-tab.active {
  color: var(--ide-text-bright);
  background: var(--ide-bg-active);
}

.editor-main {
  flex: 1 1 auto;
  overflow: hidden;
  min-height: 0;
}

.terminal-resizer {
  height: 4px;
  background: var(--ide-border);
  cursor: ns-resize;
  flex-shrink: 0;
  transition: background 0.15s;
}

.terminal-resizer:hover {
  background: var(--ide-accent);
}

.terminal-wrapper {
  flex-shrink: 0;
  overflow: hidden;
  border-top: 1px solid var(--ide-border);
}

.ai-container {
  width: 400px;
  flex-shrink: 0;
  border-left: 1px solid var(--ide-border);
  overflow: hidden;
  background: var(--ide-bg-elevated);
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
