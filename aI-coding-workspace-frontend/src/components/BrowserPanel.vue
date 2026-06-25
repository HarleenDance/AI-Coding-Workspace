<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  'update:visible': [val: boolean]
}>()

const url = ref('https://www.bing.com')
const inputUrl = ref('')
const iframeRef = ref<HTMLIFrameElement>()
const loading = ref(false)
const history = ref<string[]>([])
const historyIndex = ref(-1)
// 代理模式：通过后端剥离 X-Frame-Options，能嵌被拒绝的网站
const useProxy = ref(localStorage.getItem('browser_proxy') === 'true')
const blocked = ref(false)

const quickLinks = [
  { name: 'Bing', url: 'https://www.bing.com', icon: 'Search' },
  { name: 'MDN', url: 'https://developer.mozilla.org', icon: 'Document' },
  { name: 'Vue', url: 'https://vuejs.org', icon: 'Connection' },
  { name: 'FastAPI', url: 'https://fastapi.tiangolo.com', icon: 'Cpu' },
  { name: '本地', url: 'http://localhost:5173', icon: 'Monitor' },
  { name: 'API文档', url: 'http://localhost:8000/docs', icon: 'Files' },
]

function closePanel() {
  emit('update:visible', false)
}

function buildIframeSrc(targetUrl: string): string {
  if (useProxy.value) {
    // 代理模式：走后端剥离 X-Frame-Options
    return `/api/browser/proxy?url=${encodeURIComponent(targetUrl)}`
  }
  return targetUrl
}

function navigate(target?: string) {
  let targetUrl = (target || inputUrl.value || url.value).trim()
  if (!targetUrl) return

  // 自动补全协议
  if (!targetUrl.startsWith('http://') && !targetUrl.startsWith('https://')) {
    if (targetUrl.includes('.') || targetUrl.includes('localhost')) {
      targetUrl = 'https://' + targetUrl
    } else {
      targetUrl = 'https://www.bing.com/search?q=' + encodeURIComponent(targetUrl)
    }
  }

  url.value = targetUrl
  inputUrl.value = targetUrl
  loading.value = true
  blocked.value = false

  // 加入历史
  if (historyIndex.value < history.value.length - 1) {
    history.value = history.value.slice(0, historyIndex.value + 1)
  }
  history.value.push(targetUrl)
  historyIndex.value = history.value.length - 1

  nextTick(() => {
    if (iframeRef.value) {
      iframeRef.value.src = buildIframeSrc(targetUrl)
    }
  })
}

function toggleProxy() {
  useProxy.value = !useProxy.value
  localStorage.setItem('browser_proxy', String(useProxy.value))
  // 重新加载当前页
  if (url.value) {
    loading.value = true
    nextTick(() => {
      if (iframeRef.value) iframeRef.value.src = buildIframeSrc(url.value)
    })
  }
}

function retryWithProxy() {
  useProxy.value = true
  localStorage.setItem('browser_proxy', 'true')
  navigate(url.value)
}

function goBack() {
  if (historyIndex.value > 0) {
    historyIndex.value--
    url.value = history.value[historyIndex.value]
    inputUrl.value = url.value
    loading.value = true
    nextTick(() => {
      if (iframeRef.value) iframeRef.value.src = buildIframeSrc(url.value)
    })
  }
}

function goForward() {
  if (historyIndex.value < history.value.length - 1) {
    historyIndex.value++
    url.value = history.value[historyIndex.value]
    inputUrl.value = url.value
    loading.value = true
    nextTick(() => {
      if (iframeRef.value) iframeRef.value.src = buildIframeSrc(url.value)
    })
  }
}

function reload() {
  loading.value = true
  if (iframeRef.value) {
    iframeRef.value.src = buildIframeSrc(url.value)
  }
}

function onIframeLoad() {
  loading.value = false
  // 尝试读取 iframe 标题（同源才能读到）
  try {
    const title = iframeRef.value?.contentDocument?.title
    if (title) {
      // 可用于显示当前页面标题
    }
  } catch {
    // 跨域，无法读取（正常）
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') {
    navigate()
  }
}

// 快捷书签
function openLink(linkUrl: string) {
  inputUrl.value = linkUrl
  navigate(linkUrl)
}
</script>

<template>
  <div class="browser-panel">
    <!-- 工具栏 -->
    <div class="browser-toolbar">
      <div class="nav-buttons">
        <el-button text size="small" :disabled="historyIndex <= 0" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <el-button text size="small" :disabled="historyIndex >= history.length - 1" @click="goForward">
          <el-icon><ArrowRight /></el-icon>
        </el-button>
        <el-button text size="small" @click="reload">
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>

      <div class="url-bar">
        <el-icon class="url-icon"><Link /></el-icon>
        <input
          v-model="inputUrl"
          class="url-input"
          placeholder="输入网址或搜索..."
          @keydown="onKeydown"
          @focus="$event.target.select()"
        />
      </div>

      <div class="action-buttons">
        <el-tooltip :content="useProxy ? '代理模式已开启（点击关闭）' : '代理模式已关闭（点击开启，可嵌入被拒绝的网站）'" placement="bottom">
          <el-button text size="small" :type="useProxy ? 'primary' : 'default'" @click="toggleProxy">
            <el-icon><Connection /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip content="关闭浏览器" placement="bottom">
          <el-button text size="small" @click="closePanel">
            <el-icon><Close /></el-icon>
          </el-button>
        </el-tooltip>
      </div>
    </div>

    <!-- 快捷书签栏 -->
    <div class="bookmark-bar">
      <div
        v-for="link in quickLinks"
        :key="link.url"
        class="bookmark-item"
        @click="openLink(link.url)"
      >
        <el-icon><component :is="link.icon" /></el-icon>
        <span>{{ link.name }}</span>
      </div>
    </div>

    <!-- 浏览器内容 -->
    <div class="browser-content">
      <div v-if="loading" class="loading-bar">
        <div class="loading-progress"></div>
      </div>
      <iframe
        ref="iframeRef"
        class="browser-iframe"
        :src="buildIframeSrc(url)"
        sandbox="allow-same-origin allow-scripts allow-popups allow-forms allow-downloads"
        referrerpolicy="no-referrer"
        @load="onIframeLoad"
      ></iframe>

      <!-- 被拒绝时的提示遮罩 -->
      <div v-if="blocked" class="blocked-overlay">
        <el-icon :size="40" color="var(--ide-text-dim)"><Warning /></el-icon>
        <p style="margin: 12px 0 4px">该网站拒绝了嵌入请求</p>
        <p style="font-size: 12px; color: var(--ide-text-dim); margin: 0 0 16px">
          网站设置了 X-Frame-Options，无法直接嵌入
        </p>
        <el-button type="primary" size="small" @click="retryWithProxy">
          <el-icon><Connection /></el-icon>
          用代理模式重试
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.browser-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--ide-bg);
}

.browser-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: var(--ide-bg-elevated);
  border-bottom: 1px solid var(--ide-border);
  flex-shrink: 0;
}

.nav-buttons {
  display: flex;
  gap: 2px;
}

.url-bar {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--ide-bg);
  border: 1px solid var(--ide-border);
  border-radius: 4px;
  padding: 4px 8px;
  height: 28px;
}

.url-bar:focus-within {
  border-color: var(--ide-accent);
}

.url-icon {
  color: var(--ide-text-dim);
  flex-shrink: 0;
}

.url-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  color: var(--ide-text);
  font-size: 13px;
}

.action-buttons {
  display: flex;
  gap: 2px;
}

.bookmark-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: var(--ide-bg-elevated);
  border-bottom: 1px solid var(--ide-border);
  flex-shrink: 0;
  overflow-x: auto;
}

.bookmark-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  font-size: 12px;
  color: var(--ide-text-dim);
  cursor: pointer;
  border-radius: 3px;
  white-space: nowrap;
  transition: all 0.15s;
}

.bookmark-item:hover {
  background: var(--ide-bg-hover);
  color: var(--ide-text);
}

.browser-content {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: white;
}

.loading-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  z-index: 10;
  background: var(--ide-border);
  overflow: hidden;
}

.loading-progress {
  height: 100%;
  background: var(--ide-accent);
  animation: loading-slide 1.5s ease-in-out infinite;
}

@keyframes loading-slide {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.browser-iframe {
  width: 100%;
  height: 100%;
  border: none;
  background: white;
}

.blocked-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--ide-bg);
  color: var(--ide-text);
  font-size: 14px;
  z-index: 5;
}
</style>
