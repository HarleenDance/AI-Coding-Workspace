<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'

export type ActivityView = 'explorer' | 'search' | 'git' | 'ai' | 'settings'

const props = defineProps<{
  modelValue: ActivityView
}>()

const emit = defineEmits<{
  'update:modelValue': [value: ActivityView]
}>()

const { t } = useI18n()
const store = useAppStore()

const items = computed(() => [
  { id: 'explorer' as const, icon: 'Files', label: t('activity.explorer'), badge: 0 },
  { id: 'search' as const, icon: 'Search', label: t('activity.search'), badge: 0 },
  { id: 'git' as const, icon: 'Connection', label: t('activity.git'), badge: 0 },
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

    <!-- 底部设置 -->
    <div class="spacer"></div>
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
  width: 48px;
  background: var(--ide-bg-darker, #11111b);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 4px 0;
  flex-shrink: 0;
  border-right: 1px solid var(--ide-border);
}

.activity-item {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--ide-text-dim);
  position: relative;
  transition: color 0.15s;
}

.activity-item:hover {
  color: var(--ide-text);
}

.activity-item.active {
  color: var(--ide-text-bright);
}

.activity-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 2px;
  background: var(--ide-accent);
  border-radius: 0 2px 2px 0;
}

.badge {
  position: absolute;
  top: 6px;
  right: 6px;
  background: var(--ide-accent);
  color: #1e1e2e;
  font-size: 10px;
  min-width: 16px;
  height: 16px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
}

.spacer {
  flex: 1;
}
</style>
