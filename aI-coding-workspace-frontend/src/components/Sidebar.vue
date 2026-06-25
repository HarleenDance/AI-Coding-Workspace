<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { useAppStore } from '@/stores/app'
import FileTreeNodeItem from './FileTreeNodeItem.vue'

const { t } = useI18n()
const store = useAppStore()
const collapsed = ref(false)
const fileInput = ref<HTMLInputElement>()
const folderInput = ref<HTMLInputElement>()
const dragOver = ref(false)

onMounted(() => {
  store.loadProjects()
})

function triggerUpload() {
  fileInput.value?.click()
}

function triggerFolderUpload() {
  folderInput.value?.click()
}

async function handleUpload(e: Event) {
  const target = e.target as HTMLInputElement
  if (!target.files?.length) return
  await store.uploadProject(target.files[0])
  target.value = ''
}

async function handleFolderUpload(e: Event) {
  const target = e.target as HTMLInputElement
  if (!target.files?.length) return
  const fileList = Array.from(target.files)
  await store.uploadFolder(fileList)
  target.value = ''
}

// 拖拽上传
function onDrop(e: DragEvent) {
  dragOver.value = false
  if (!e.dataTransfer?.files.length) return
  const file = e.dataTransfer.files[0]
  if (file.name.endsWith('.zip')) {
    store.uploadProject(file)
  } else {
    ElMessage.info('请拖入 .zip 文件，或使用「上传文件夹」按钮')
  }
}
</script>

<template>
  <div class="sidebar" :class="{ collapsed }">
    <div class="sidebar-header">
      <el-select
        v-if="!collapsed"
        v-model="store.projectId"
        placeholder="选择项目"
        size="small"
        class="project-select"
        @change="(val: string) => store.selectProject(val)"
      >
        <el-option
          v-for="p in store.projects"
          :key="p.id"
          :label="p.name"
          :value="p.id"
        >
          <span>{{ p.name }}</span>
          <el-tag v-if="p.is_indexed" size="small" type="success" style="margin-left: 8px">{{ t('sidebar.indexed') }}</el-tag>
        </el-option>
      </el-select>
      <el-button text size="small" @click="collapsed = !collapsed">
        <el-icon>
          <Fold v-if="!collapsed" />
          <Expand v-else />
        </el-icon>
      </el-button>
    </div>

    <div v-if="!collapsed" class="upload-section">
      <input
        ref="fileInput"
        type="file"
        accept=".zip"
        style="display: none"
        @change="handleUpload"
      />
      <input
        ref="folderInput"
        type="file"
        style="display: none"
        webkitdirectory
        directory
        multiple
        @change="handleFolderUpload"
      />

      <!-- 拖拽区域 -->
      <div
        class="drop-zone"
        :class="{ active: dragOver, loading: store.uploading }"
        @click="triggerUpload"
        @dragover.prevent="dragOver = true"
        @dragleave.prevent="dragOver = false"
        @drop.prevent="onDrop"
      >
        <el-icon :size="20" class="drop-icon">
          <Upload v-if="!store.uploading" />
          <Loading v-else />
        </el-icon>
        <span class="drop-text">
          {{ store.uploading ? '上传中...' : '拖拽 ZIP 到此处' }}
        </span>
      </div>

      <!-- 两个按钮并排 -->
      <div class="upload-buttons">
        <el-button
          size="small"
          plain
          class="upload-btn"
          :loading="store.uploading"
          @click="triggerUpload"
        >
          <el-icon><Upload /></el-icon>
          <span>ZIP</span>
        </el-button>
        <el-button
          size="small"
          plain
          class="upload-btn"
          :loading="store.uploading"
          @click="triggerFolderUpload"
        >
          <el-icon><FolderOpened /></el-icon>
          <span>文件夹</span>
        </el-button>
      </div>

      <!-- 索引按钮 -->
      <el-button
        v-if="store.projectId"
        size="small"
        plain
        class="index-btn"
        :loading="store.indexing"
        @click="store.indexProject()"
      >
        <el-icon><Refresh /></el-icon>
        {{ store.currentProject?.is_indexed ? t('sidebar.reindex') : t('sidebar.buildIndex') }}
      </el-button>
    </div>

    <div v-if="!collapsed" class="sidebar-body">
      <template v-if="store.projectId">
        <div class="section-label">
          <el-icon><FolderOpened /></el-icon>
          {{ store.currentProject?.name || '文件' }}
        </div>
        <div v-if="Object.keys(store.fileTree).length === 0" class="empty-tree">
          <el-text size="small" type="info">{{ t('sidebar.noFiles') }}</el-text>
        </div>
        <FileTreeNodeItem
          v-for="(node, name) in store.fileTree"
          :key="name"
          :name="String(name)"
          :node="node"
          :depth="0"
        />
      </template>
      <template v-else>
        <div class="empty-tree">
          <el-text size="small" type="info">{{ t('sidebar.selectOrUpload') }}</el-text>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.sidebar {
  width: 260px;
  background: var(--ide-bg-elevated);
  display: flex;
  flex-direction: column;
  transition: width 0.2s;
  flex-shrink: 0;
  overflow: hidden;
}
.sidebar.collapsed {
  width: 44px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--ide-border);
}
.project-select {
  flex: 1;
}

.upload-section {
  padding: 10px;
  border-bottom: 1px solid var(--ide-border);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 拖拽区域 */
.drop-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 16px 8px;
  border: 1.5px dashed var(--ide-border);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--ide-text-dim);
  background: var(--ide-bg);
}
.drop-zone:hover {
  border-color: var(--ide-accent);
  color: var(--ide-accent);
  background: rgba(137, 180, 250, 0.04);
}
.drop-zone.active {
  border-color: var(--ide-accent);
  border-style: solid;
  background: rgba(137, 180, 250, 0.1);
  color: var(--ide-accent);
  transform: scale(1.02);
}
.drop-zone.loading {
  pointer-events: none;
  opacity: 0.7;
}
.drop-icon {
  transition: transform 0.2s;
}
.drop-zone:hover .drop-icon {
  transform: translateY(-2px);
}
.drop-text {
  font-size: 11px;
  font-weight: 500;
}

/* 按钮并排 */
.upload-buttons {
  display: flex;
  gap: 6px;
}
.upload-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin: 0 !important;
}
.upload-btn :deep(span) {
  font-size: 12px;
}

/* 索引按钮 */
.index-btn {
  width: 100%;
  margin: 0 !important;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.sidebar-body {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 11px;
  color: var(--ide-text-dim);
  font-weight: 600;
  text-transform: uppercase;
}

.empty-tree {
  padding: 20px 12px;
  text-align: center;
}
</style>
