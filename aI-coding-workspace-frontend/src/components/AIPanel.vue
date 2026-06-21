<script setup lang="ts">
import { ref } from 'vue'
import ChatTab from './ChatTab.vue'
import VibeTab from './VibeTab.vue'
import EventsTab from './EventsTab.vue'

const activeTab = ref<'chat' | 'vibe' | 'events'>('chat')
</script>

<template>
  <div class="ai-panel flex-col full-h">
    <div class="tab-header">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'chat' }"
        @click="activeTab = 'chat'"
      >
        <el-icon><ChatDotRound /></el-icon>
        Chat
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'vibe' }"
        @click="activeTab = 'vibe'"
      >
        <el-icon><MagicStick /></el-icon>
        Vibe
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'events' }"
        @click="activeTab = 'events'"
      >
        <el-icon><DataLine /></el-icon>
        Events
      </button>
    </div>

    <div class="tab-body flex-1">
      <ChatTab v-show="activeTab === 'chat'" />
      <VibeTab v-show="activeTab === 'vibe'" />
      <EventsTab v-show="activeTab === 'events'" />
    </div>
  </div>
</template>

<style scoped>
.ai-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--ide-bg);
}

.tab-header {
  display: flex;
  border-bottom: 1px solid var(--ide-border);
  background: var(--ide-bg-elevated);
}

.tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 0;
  background: none;
  border: none;
  color: var(--ide-text-dim);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
  border-bottom: 2px solid transparent;
}

.tab-btn:hover {
  color: var(--ide-text);
  background: var(--ide-bg-hover);
}

.tab-btn.active {
  color: var(--ide-accent);
  border-bottom-color: var(--ide-accent);
  background: var(--ide-bg-active);
}

.tab-body {
  flex: 1;
  overflow: hidden;
}
</style>
