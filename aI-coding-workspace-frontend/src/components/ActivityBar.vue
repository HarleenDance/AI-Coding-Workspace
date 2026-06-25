<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'

export type ActivityView = 'explorer' | 'search' | 'git' | 'yuque' | 'ai' | 'settings'

const props = defineProps<{
  modelValue: ActivityView
}>()

const emit = defineEmits<{
  'update:modelValue': [value: ActivityView]
  'toggle-terminal': []
}>()

const { t } = useI18n()
const store = useAppStore()

const items = computed(() => [
  { id: 'explorer' as const, icon: 'Files', label: t('activity.explorer'), badge: 0 },
  { id: 'search' as const, icon: 'Search', label: t('activity.search'), badge: 0 },
  { id: 'git' as const, icon: 'Connection', label: t('activity.git'), badge: 0 },
  { id: 'yuque' as const, icon: 'Reading', label: '语雀文档', badge: 0 },
  { id: 'ai' as const, icon: 'ChatDotRound', label: t('activity.ai'), badge: store.chatLoading ? 1 : 0 },
])

function select(id: ActivityView) {
  emit('update:modelValue', id)
}
</script>

<template>
  <div class="activity-bar">
    <div
      v-for="item in items"
      :key="item.id"
      class="activity-item"
      :class="{ active: modelValue === item.id }"
      @click="select(item.id)"
    >
      <el-icon :size="22">
        <component :is="item.icon" />
      </el-icon>
      <span v-if="item.badge" class="badge">{{ item.badge }}</span>
    </div>

    <!-- 底部终端 -->
    <div class="spacer"></div>
    <div
      class="activity-item"
      @click="emit('toggle-terminal')"
    >
      <el-tooltip content="终端 (Ctrl+`)" placement="right">
        <el-icon :size="22"><Monitor /></el-icon>
      </el-tooltip>
    </div>
    <div
      class="activity-item"
      :class="{ active: modelValue === 'settings' }"
      @click="select('settings')"
    >
      <el-tooltip :content="t('activity.settings')" placement="right">
        <el-icon :size="22"><Setting /></el-icon>
      </el-tooltip>
    </div>
  </div>
</template>

<style scoped>
.activity-bar {
  width: 44px;
  background: var(--ide-bg-darker);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 6px 0;
  flex-shrink: 0;
  border-right: 1px solid var(--ide-border);
}

.activity-item {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--ide-text-dim);
  position: relative;
  transition: all 0.15s ease;
  border-radius: 8px;
  margin: 1px 4px;
}

.activity-item:hover {
  color: var(--ide-text);
  background: rgba(255, 255, 255, 0.04);
}

.activity-item.active {
  color: var(--ide-text-bright);
  background: rgba(255, 255, 255, 0.06);
}

.activity-item.active::before {
  content: '';
  position: absolute;
  left: -4px;
  top: 10px;
  bottom: 10px;
  width: 3px;
  background: var(--ide-accent);
  border-radius: 0 3px 3px 0;
  box-shadow: 0 0 8px var(--ide-accent-glow);
}

.badge {
  position: absolute;
  top: 7px;
  right: 7px;
  background: var(--ide-accent);
  color: var(--ide-bg-darker);
  font-size: 9px;
  min-width: 14px;
  height: 14px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  padding: 0 3px;
}

.spacer {
  flex: 1;
}
</style>
