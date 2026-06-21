<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'

const { t } = useI18n()

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  'update:visible': [val: boolean]
  command: [action: string]
}>()

const store = useAppStore()
const query = ref('')
const selectedIndex = ref(0)
const inputRef = ref<HTMLInputElement>()
const mode = computed(() => (query.value.startsWith('>') ? 'command' : 'file'))

interface CmdItem {
  type: 'file' | 'command'
  label: string
  detail?: string
  action: () => void
}

const results = computed<CmdItem[]>(() => {
  if (mode.value === 'command') {
    const q = query.value.slice(1).toLowerCase()
    const commands: CmdItem[] = [
      { type: 'command', label: 'Upload Project', detail: 'Upload a ZIP file', action: () => document.getElementById('global-upload-input')?.click() },
      { type: 'command', label: 'Index Project', detail: 'Build embedding index', action: () => store.indexProject() },
      { type: 'command', label: 'Clear Chat', detail: 'Clear chat history', action: () => store.clearChat() },
      { type: 'command', label: 'View: Explorer', detail: 'Switch to file explorer', action: () => emit('command', 'view-explorer') },
      { type: 'command', label: 'View: Search', detail: 'Switch to search', action: () => emit('command', 'view-search') },
      { type: 'command', label: 'View: AI Assistant', detail: 'Switch to AI panel', action: () => emit('command', 'view-ai') },
      { type: 'command', label: 'Check Health', detail: 'Check database connection', action: () => store.checkHealth() },
    ]
    return q ? commands.filter((c) => c.label.toLowerCase().includes(q)) : commands
  } else {
    const q = query.value.toLowerCase()
    const files: CmdItem[] = []
    function walk(nodes: Record<string, { _type: string; _path?: string; _children?: Record<string, unknown> }>) {
      for (const [name, node] of Object.entries(nodes)) {
        if (node._type === 'file' && node._path) {
          if (!q || node._path.toLowerCase().includes(q) || name.toLowerCase().includes(q)) {
            files.push({ type: 'file', label: name, detail: node._path, action: () => { store.openFile(node._path!); close() } })
          }
        } else if (node._children) {
          walk(node._children as Record<string, { _type: string; _path?: string; _children?: Record<string, unknown> }>)
        }
      }
    }
    walk(store.fileTree)
    return files.slice(0, 30)
  }
})

watch(results, () => { selectedIndex.value = 0 })

function close() {
  query.value = ''
  emit('update:visible', false)
}

function executeSelected() {
  const item = results.value[selectedIndex.value]
  if (item) {
    item.action()
    if (item.type === 'command') close()
  }
}

function onKeydown(e: KeyboardEvent) {
  if (!props.visible) return
  if (e.key === 'ArrowDown') { e.preventDefault(); selectedIndex.value = Math.min(selectedIndex.value + 1, results.value.length - 1) }
  if (e.key === 'ArrowUp') { e.preventDefault(); selectedIndex.value = Math.max(selectedIndex.value - 1, 0) }
  if (e.key === 'Enter') { e.preventDefault(); executeSelected() }
  if (e.key === 'Escape') { e.preventDefault(); close() }
}

watch(() => props.visible, (v) => {
  if (v) {
    query.value = ''
    selectedIndex.value = 0
    setTimeout(() => inputRef.value?.focus(), 50)
  }
})

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="cmd-overlay" @click.self="close">
      <div class="cmd-panel">
        <div class="cmd-input-wrap">
          <el-icon class="cmd-icon"><Search /></el-icon>
          <input
            ref="inputRef"
            v-model="query"
            class="cmd-input"
            :placeholder="mode === 'command' ? t('command.typeCommand') : t('command.searchFiles')"
            spellcheck="false"
          />
          <span class="cmd-mode">{{ mode === 'command' ? t('command.commands') : t('command.files') }}</span>
        </div>
        <div class="cmd-list">
          <div
            v-for="(item, i) in results"
            :key="i"
            class="cmd-item"
            :class="{ selected: i === selectedIndex }"
            @mouseenter="selectedIndex = i"
            @click="executeSelected"
          >
            <el-icon class="cmd-item-icon">
              <Document v-if="item.type === 'file'" />
              <Operation v-else />
            </el-icon>
            <div class="cmd-item-text">
              <span class="cmd-item-label">{{ item.label }}</span>
              <span v-if="item.detail" class="cmd-item-detail">{{ item.detail }}</span>
            </div>
          </div>
          <div v-if="results.length === 0" class="cmd-empty">
            {{ t('command.noResults') }}
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.cmd-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 3000;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 80px;
}

.cmd-panel {
  background: var(--ide-bg-elevated);
  border: 1px solid var(--ide-border-light);
  border-radius: 8px;
  width: 90%;
  max-width: 600px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}

.cmd-input-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--ide-border);
}

.cmd-icon {
  color: var(--ide-text-dim);
  font-size: 16px;
}

.cmd-input {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  color: var(--ide-text);
  font-size: 14px;
  font-family: inherit;
}

.cmd-input::placeholder {
  color: var(--ide-text-dim);
}

.cmd-mode {
  font-size: 11px;
  color: var(--ide-text-dim);
  background: var(--ide-bg-active);
  padding: 2px 8px;
  border-radius: 4px;
}

.cmd-list {
  max-height: 400px;
  overflow-y: auto;
  padding: 4px;
}

.cmd-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
}

.cmd-item.selected {
  background: var(--ide-accent);
}

.cmd-item.selected .cmd-item-label,
.cmd-item.selected .cmd-item-detail,
.cmd-item.selected .cmd-item-icon {
  color: #1e1e2e;
}

.cmd-item-icon {
  color: var(--ide-text-dim);
  font-size: 16px;
  flex-shrink: 0;
}

.cmd-item-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.cmd-item-label {
  font-size: 13px;
  color: var(--ide-text);
}

.cmd-item-detail {
  font-size: 11px;
  color: var(--ide-text-dim);
  font-family: var(--ide-mono);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cmd-empty {
  padding: 24px;
  text-align: center;
  color: var(--ide-text-dim);
  font-size: 13px;
}
</style>
