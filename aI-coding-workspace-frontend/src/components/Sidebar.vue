<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import FileTreeNodeItem from './FileTreeNodeItem.vue'

const { t } = useI18n()
const store = useAppStore()
const collapsed = ref(false)
const fileInput = ref<HTMLInputElement>()

onMounted(() => {
  store.loadProjects()
})

function triggerUpload() {
  fileInput.value?.click()
}

async function handleUpload(e: Event) {
  const target = e.target as HTMLInputElement
  if (!target.files?.length) return
  await store.uploadProject(target.files[0])
  target.value = ''
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
      <el-button
        type="primary"
        size="small"
        plain
        class="upload-btn"
        :loading="store.uploading"
        @click="triggerUpload"
      >
        <el-icon><Upload /></el-icon>
        {{ t('sidebar.uploadZip') }}
      </el-button>
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
  border-right: 1px solid var(--ide-border);
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
  padding: 8px;
  border-bottom: 1px solid var(--ide-border);
}
.project-select {
  flex: 1;
}

.upload-section {
  padding: 8px;
  border-bottom: 1px solid var(--ide-border);
}
.upload-btn {
  width: 100%;
}
.index-btn {
  width: 100%;
  margin-top: 6px;
  margin-left: 0;
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
