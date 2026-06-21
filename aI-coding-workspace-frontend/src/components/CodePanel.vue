<script setup lang="ts">
import { computed, ref } from 'vue'
import CodeEditor from './CodeEditor.vue'
import { useAppStore } from '@/stores/app'

const store = useAppStore()

const showDiff = computed(
  () => !!store.vibePlan?.diff && store.vibePlan.status === 'completed',
)

const language = computed(() => {
  if (showDiff.value) return 'diff'
  return store.currentFile?.language || 'plaintext'
})

const code = computed(() => {
  if (showDiff.value) return ''
  return store.currentFile?.content || welcomeContent
})

const dirty = ref(false)
const editedContent = ref('')

function onCodeChange(content: string) {
  editedContent.value = content
  dirty.value = content !== (store.currentFile?.content || '')
}

async function save() {
  if (!dirty.value) return
  await store.saveFile(editedContent.value)
  dirty.value = false
}

function onKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault()
    save()
  }
}

function getFileName(path: string): string {
  return path.split('/').pop() || path
}

const welcomeContent = `# Welcome to AI Coding Workspace
#
# How to use:
# 1. Upload a ZIP project (Explorer panel)
# 2. Click files to open them in tabs
# 3. Use AI panel:
#    - Chat: Ask questions about your codebase (RAG-powered)
#    - Vibe: Describe a feature -> AI generates plan -> Approve -> Diff
#    - Events: Real-time LangGraph event stream
#
# Shortcuts:
#   Ctrl+P       Quick open file
#   Ctrl+Shift+P Command palette
#   Ctrl+S       Save file
#
# Database: ${store.healthOk ? 'Connected' : 'Offline'}`
</script>

<template>
  <div class="code-panel" @keydown="onKeydown">
    <!-- 多 Tab 标签栏 -->
    <div class="tab-bar">
      <div
        v-for="tab in store.openTabs"
        :key="tab.path"
        class="tab-item"
        :class="{ active: store.activeTabPath === tab.path }"
        @click="store.switchTab(tab.path)"
      >
        <el-icon class="tab-icon"><Document /></el-icon>
        <span class="tab-name">{{ getFileName(tab.path) }}</span>
        <el-icon
          class="tab-close"
          @click.stop="store.closeTab(tab.path)"
        >
          <Close />
        </el-icon>
      </div>

      <!-- Vibe Diff Tab -->
      <div v-if="showDiff" class="tab-item active">
        <el-icon class="tab-icon"><Files /></el-icon>
        <span class="tab-name">Vibe Diff</span>
      </div>

      <div v-if="dirty" class="save-area">
        <el-button text size="small" @click="save">
          <el-icon><Check /></el-icon>
          Save (Ctrl+S)
        </el-button>
      </div>
    </div>

    <!-- 编辑器区 -->
    <div class="editor-area">
      <div v-if="store.fileLoading" class="loading-mask">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
      </div>
      <CodeEditor
        v-if="showDiff"
        :original="''"
        :modified="store.vibePlan?.diff || ''"
        language="diff"
      />
      <CodeEditor
        v-else-if="store.currentFile"
        :key="store.activeTabPath"
        :code="code"
        :language="language"
        :read-only="false"
        @change="onCodeChange"
        @append="(code: string) => store.appendCodeToContext(store.currentFile?.path || '', code)"
      />
      <div v-else class="welcome-screen">
        <div class="welcome-content">
          <el-icon :size="48" color="var(--ide-accent)"><Cpu /></el-icon>
          <h2>AI Coding Workspace</h2>
          <p>Upload a project to get started</p>
          <div class="shortcuts">
            <kbd>Ctrl+P</kbd> Quick Open
            <kbd>Ctrl+Shift+P</kbd> Commands
          </div>
        </div>
      </div>
    </div>

    <!-- 状态栏 -->
    <div class="status-bar">
      <span class="status-item">
        <el-icon><Connection /></el-icon>
        {{ store.healthOk ? 'DB Connected' : 'DB Offline' }}
      </span>
      <span class="status-item" v-if="store.currentFile">
        {{ (store.currentFile.size / 1024).toFixed(1) }} KB
      </span>
      <span class="spacer"></span>
      <span v-if="dirty" class="status-item" style="color: var(--ide-yellow)">Unsaved</span>
      <span class="status-item">{{ language }}</span>
    </div>
  </div>
</template>

<style scoped>
.code-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--ide-bg);
}

.tab-bar {
  display: flex;
  align-items: center;
  background: var(--ide-bg-elevated);
  border-bottom: 1px solid var(--ide-border);
  height: 36px;
  overflow-x: auto;
}

.tab-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 12px;
  height: 100%;
  font-size: 12px;
  color: var(--ide-text-dim);
  background: var(--ide-bg-elevated);
  border-right: 1px solid var(--ide-border);
  cursor: pointer;
  white-space: nowrap;
  position: relative;
  flex-shrink: 0;
}

.tab-item:hover {
  background: var(--ide-bg-hover);
}

.tab-item.active {
  background: var(--ide-bg);
  color: var(--ide-text-bright);
}

.tab-item.active::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: var(--ide-accent);
}

.tab-icon {
  font-size: 13px;
  color: var(--ide-text-dim);
}

.tab-name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tab-close {
  font-size: 12px;
  padding: 2px;
  border-radius: 3px;
  opacity: 0;
  transition: opacity 0.15s, background 0.15s;
}

.tab-item:hover .tab-close {
  opacity: 1;
}

.tab-close:hover {
  background: var(--ide-bg-active);
}

.save-area {
  margin-left: auto;
  padding-right: 8px;
  flex-shrink: 0;
}

.editor-area {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.loading-mask {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 10;
  color: var(--ide-accent);
}

.welcome-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.welcome-content {
  text-align: center;
  color: var(--ide-text-dim);
}

.welcome-content h2 {
  margin: 16px 0 8px;
  font-size: 20px;
  color: var(--ide-text);
}

.welcome-content p {
  font-size: 13px;
  margin-bottom: 24px;
}

.shortcuts {
  display: flex;
  gap: 16px;
  justify-content: center;
  font-size: 12px;
}

kbd {
  background: var(--ide-bg-elevated);
  border: 1px solid var(--ide-border);
  border-radius: 4px;
  padding: 2px 8px;
  font-family: var(--ide-mono);
  font-size: 11px;
  margin-right: 4px;
}

.status-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 12px;
  height: 24px;
  background: var(--ide-accent);
  color: #1e1e2e;
  font-size: 12px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.spacer {
  flex: 1;
}
</style>
