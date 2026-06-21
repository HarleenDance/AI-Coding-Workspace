<script setup lang="ts">
import { useAppStore } from '@/stores/app'

const store = useAppStore()
</script>

<template>
  <div class="topbar-wrapper">
  <div class="topbar">
    <div class="left">
      <el-icon class="logo" color="var(--ide-accent)" :size="20"><Cpu /></el-icon>
      <span class="app-name">AI Coding Workspace</span>
    </div>

    <!-- 搜索框 -->
    <div class="search-area" v-if="store.projectId">
      <el-input
        v-model="store.searchQuery"
        size="small"
        placeholder="搜索代码... (Ctrl+K)"
        class="search-input"
        @keydown.enter="store.runSearch()"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-radio-group v-model="store.searchMode" size="small" class="search-mode">
        <el-radio-button value="keyword">关键词</el-radio-button>
        <el-radio-button value="semantic">语义</el-radio-button>
      </el-radio-group>
    </div>

    <div class="center">
      <span class="db-status" :class="{ ok: store.healthOk, bad: store.healthOk === false }">
        <span class="status-dot"></span>
        {{ store.healthOk === null ? '检查中...' : store.healthOk ? '已连接' : '未连接' }}
      </span>
    </div>

    <div class="right">
      <el-tooltip content="刷新健康检查" placement="bottom">
        <el-button text size="small" @click="store.checkHealth">
          <el-icon><Refresh /></el-icon>
        </el-button>
      </el-tooltip>
    </div>
  </div>

  <!-- 搜索结果浮层 -->
  <Teleport to="body">
    <div v-if="store.showSearch" class="search-overlay" @click.self="store.clearSearch()">
      <div class="search-panel">
        <div class="search-header">
          <span>搜索 "{{ store.searchQuery }}" — {{ store.searchResults.length }} 个结果</span>
          <el-button text size="small" @click="store.clearSearch()">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
        <div class="search-list">
          <div
            v-for="(r, i) in store.searchResults"
            :key="i"
            class="search-item"
            @click="store.openFile(r.file_path); store.clearSearch()"
          >
            <div class="search-item-header">
              <el-icon><Document /></el-icon>
              <span class="search-file">{{ r.file_path }}</span>
              <el-tag size="small" type="info">
                {{ r.match_count || r.score.toFixed(2) }}
              </el-tag>
            </div>
            <pre class="search-snippet">{{ r.content }}</pre>
          </div>
          <div v-if="store.searchResults.length === 0" class="search-empty">
            <el-text type="info">没有匹配结果</el-text>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
  </div>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 40px;
  padding: 0 12px;
  background: var(--ide-bg-elevated);
  border-bottom: 1px solid var(--ide-border);
  flex-shrink: 0;
  gap: 12px;
}

.left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.app-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--ide-text-bright);
  white-space: nowrap;
}

.search-area {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  max-width: 500px;
}

.search-input {
  flex: 1;
}

.search-mode {
  flex-shrink: 0;
}

.center {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.db-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--ide-text-dim);
  padding: 3px 10px;
  border-radius: 12px;
  background: var(--ide-bg-active);
  white-space: nowrap;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--ide-text-dim);
}
.db-status.ok .status-dot {
  background: var(--ide-green);
  box-shadow: 0 0 6px var(--ide-green);
}
.db-status.bad .status-dot {
  background: var(--ide-red);
  box-shadow: 0 0 6px var(--ide-red);
}

.right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

/* 搜索浮层 */
.search-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 2000;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 60px;
}

.search-panel {
  background: var(--ide-bg-elevated);
  border: 1px solid var(--ide-border-light);
  border-radius: 8px;
  width: 90%;
  max-width: 700px;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

.search-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--ide-border);
  font-size: 13px;
  color: var(--ide-text-dim);
}

.search-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.search-item {
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 4px;
}
.search-item:hover {
  background: var(--ide-bg-hover);
}

.search-item-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.search-file {
  font-size: 13px;
  color: var(--ide-accent);
  font-family: var(--ide-mono);
}

.search-snippet {
  font-family: var(--ide-mono);
  font-size: 12px;
  color: var(--ide-text-dim);
  background: var(--ide-bg);
  padding: 6px 8px;
  border-radius: 4px;
  margin: 0;
  overflow-x: auto;
  max-height: 100px;
}

.search-empty {
  padding: 40px;
  text-align: center;
}

@media (max-width: 768px) {
  .search-area {
    display: none;
  }
}
</style>
