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
  background: var(--ide-bg-elevated);
}

.tab-header {
  display: flex;
  border-bottom: 1px solid var(--ide-border);
  background: var(--ide-bg-darker);
  height: 36px;
}

.tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 0;
  background: none;
  border: none;
  color: var(--ide-text-dim);
  cursor: pointer;
  font-size: 12px;
  transition: all 0.15s;
  position: relative;
}

.tab-btn:hover {
  color: var(--ide-text);
}

.tab-btn.active {
  color: var(--ide-text-bright);
}

.tab-btn.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 20%;
  right: 20%;
  height: 2px;
  background: var(--ide-accent);
  border-radius: 2px 2px 0 0;
}

.tab-body {
  flex: 1;
  overflow: hidden;
}
</style>
