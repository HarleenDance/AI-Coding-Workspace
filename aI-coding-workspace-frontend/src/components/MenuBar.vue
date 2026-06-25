<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import { ElMessage } from 'element-plus'
import { setLanguage, getLanguage } from '@/i18n'

const { t } = useI18n()
const store = useAppStore()
const openMenu = ref<string | null>(null)
const currentLang = ref(getLanguage())

const menus = computed(() => ({
  [t('menu.file')]: [
    { label: t('menuItems.uploadProject'), shortcut: 'Ctrl+U', action: 'upload' },
    { label: t('menuItems.newFile'), shortcut: 'Ctrl+N', action: 'newfile' },
    { label: t('menuItems.saveFile'), shortcut: 'Ctrl+S', action: 'save' },
    { divider: true },
    { label: t('menuItems.indexProject'), shortcut: '', action: 'index' },
    { label: t('menuItems.closeTab'), shortcut: 'Ctrl+W', action: 'closetab' },
  ],
  [t('menu.view')]: [
    { label: t('menuItems.explorer'), shortcut: 'Ctrl+Shift+E', action: 'view-explorer' },
    { label: t('menuItems.search'), shortcut: 'Ctrl+Shift+F', action: 'view-search' },
    { label: t('menuItems.aiAssistant'), shortcut: 'Ctrl+Shift+A', action: 'view-ai' },
    { divider: true },
    { label: t('menuItems.commandPalette'), shortcut: 'Ctrl+Shift+P', action: 'cmd' },
  ],
  [t('menu.run')]: [
    { label: t('menuItems.startBackend'), shortcut: '', action: 'run-backend' },
    { label: t('menuItems.startFrontend'), shortcut: '', action: 'run-frontend' },
    { divider: true },
    { label: t('menuItems.toggleTerminal'), shortcut: 'Ctrl+`', action: 'terminal' },
  ],
  [t('menu.help')]: [
    { label: t('menuItems.documentation'), shortcut: '', action: 'docs' },
    { label: t('menuItems.apiReference'), shortcut: '', action: 'api' },
    { label: t('menuItems.about'), shortcut: '', action: 'about' },
  ],
}))

function toggleMenu(name: string) {
  openMenu.value = openMenu.value === name ? null : name
}

function handleAction(action: string) {
  openMenu.value = null
  switch (action) {
    case 'upload':
      document.getElementById('global-upload-input')?.click()
      break
    case 'save':
      ElMessage.info(t('editor.save'))
      break
    case 'index':
      store.indexProject()
      break
    case 'view-explorer':
      emit('view', 'explorer')
      break
    case 'view-search':
      emit('view', 'search')
      break
    case 'view-ai':
      emit('view', 'ai')
      break
    case 'cmd':
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'P', shiftKey: true, ctrlKey: true }))
      break
    case 'docs':
    case 'api':
      window.open('http://localhost:8000/docs', '_blank')
      break
    case 'about':
      ElMessage.info('AI Coding Workspace v1.0')
      break
    default:
      ElMessage.info(action)
  }
}

function changeLang(lang: 'zh' | 'en') {
  setLanguage(lang)
  currentLang.value = lang
  openMenu.value = null
}

const emit = defineEmits<{ view: [target: string] }>()
</script>

<template>
  <div class="menu-bar" @mouseleave="openMenu = null">
    <div
      v-for="(items, name) in menus"
      :key="name"
      class="menu-item"
      :class="{ active: openMenu === name }"
      @mouseenter="openMenu = openMenu ? name : null"
      @click="toggleMenu(name)"
    >
      {{ name }}
      <transition name="menu-drop">
        <div v-if="openMenu === name" class="menu-dropdown">
          <template v-for="(item, i) in items" :key="i">
            <div v-if="item.divider" class="menu-divider"></div>
            <div v-else class="menu-option" @click.stop="handleAction(item.action)">
              <span>{{ item.label }}</span>
              <span v-if="item.shortcut" class="shortcut">{{ item.shortcut }}</span>
            </div>
          </template>
        </div>
      </transition>
    </div>

    <!-- 语言切换 -->
    <div class="menu-item lang-switch" @click="openMenu = openMenu === '__lang' ? null : '__lang'">
      <el-icon><svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M12.87 15.07l-2.54-2.51.03-.03c1.74-1.94 2.98-4.17 3.71-6.53H17V4h-7V2H8v2H1v1.99h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11.76-2.04zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2l-4.5-12zm-2.62 7l1.62-4.33L19.12 17h-3.24z"/></svg></el-icon>
      <transition name="menu-drop">
        <div v-if="openMenu === '__lang'" class="menu-dropdown">
          <div class="menu-option" :class="{ 'lang-active': currentLang === 'zh' }" @click.stop="changeLang('zh')">
            <span>中文</span>
            <el-icon v-if="currentLang === 'zh'"><Check /></el-icon>
          </div>
          <div class="menu-option" :class="{ 'lang-active': currentLang === 'en' }" @click.stop="changeLang('en')">
            <span>English</span>
            <el-icon v-if="currentLang === 'en'"><Check /></el-icon>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<style scoped>
.menu-bar {
  display: flex;
  align-items: center;
  height: 28px;
  background: var(--ide-bg-darker);
  padding: 0 4px;
  border-bottom: 1px solid var(--ide-border);
  flex-shrink: 0;
  user-select: none;
}

.menu-item {
  position: relative;
  padding: 0 10px;
  height: 20px;
  margin: 2px 1px;
  display: flex;
  align-items: center;
  font-size: 12px;
  color: var(--ide-text);
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.12s;
}

.menu-item:hover { background: var(--ide-bg-hover); }
.menu-item.active { background: var(--ide-bg-active); }

.lang-switch {
  margin-left: auto;
  display: flex;
  align-items: center;
  color: var(--ide-text-dim);
}

.lang-active { color: var(--ide-accent); }

.menu-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  min-width: 220px;
  background: var(--ide-bg-elevated);
  border: 1px solid var(--ide-border-light);
  border-radius: 6px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  padding: 4px;
  z-index: 1000;
}

.menu-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  font-size: 12px;
  color: var(--ide-text);
  border-radius: 4px;
  cursor: pointer;
}

.menu-option:hover { background: var(--ide-accent); color: #1e1e2e; }

.shortcut {
  font-size: 11px;
  color: var(--ide-text-dim);
  margin-left: 24px;
}

.menu-option:hover .shortcut { color: rgba(30, 30, 46, 0.7); }

.menu-divider { height: 1px; background: var(--ide-border); margin: 4px 8px; }

.menu-drop-enter-active, .menu-drop-leave-active { transition: opacity 0.1s, transform 0.1s; }
.menu-drop-enter-from, .menu-drop-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
