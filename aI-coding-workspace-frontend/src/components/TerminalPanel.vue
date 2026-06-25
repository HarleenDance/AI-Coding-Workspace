<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import '@xterm/xterm/css/xterm.css'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  'update:visible': [val: boolean]
}>()

const terminalRef = ref<HTMLDivElement>()
let term: Terminal | null = null
let fitAddon: FitAddon | null = null
let ws: WebSocket | null = null
let resizeObserver: ResizeObserver | null = null

function closePanel() {
  emit('update:visible', false)
}

function initTerminal() {
  if (term || !terminalRef.value) return

  term = new Terminal({
    fontSize: 13,
    fontFamily: "'Cascadia Code', 'Fira Code', 'Consolas', monospace",
    cursorBlink: true,
    theme: {
      background: '#181818',
      foreground: '#d4d4d4',
      cursor: '#aeafad',
      selectionBackground: '#264f78',
      black: '#000000',
      red: '#f14c4c',
      green: '#4ec9b0',
      yellow: '#dcdcaa',
      blue: '#569cd6',
      magenta: '#c586c0',
      cyan: '#4ec9b0',
      white: '#d4d4d4',
      brightBlack: '#808080',
      brightRed: '#f14c4c',
      brightGreen: '#4ec9b0',
      brightYellow: '#dcdcaa',
      brightBlue: '#569cd6',
      brightMagenta: '#c586c0',
      brightCyan: '#4ec9b0',
      brightWhite: '#ffffff',
    },
  })

  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.loadAddon(new WebLinksAddon())
  term.open(terminalRef.value)
  fitAddon.fit()

  // 连接 WebSocket
  // 开发环境直连后端 8000 端口（避免 Vite proxy 未配置 ws 的问题）
  // 生产环境走同源（nginx 已配置 /api/ws 转发）
  const wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const isDev = location.port === '5173'
  const wsHost = isDev ? `${location.hostname}:8000` : location.host
  const wsUrl = `${wsProtocol}//${wsHost}/api/ws/terminal`
  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    term?.writeln('\x1b[32m✓ 终端连接成功\x1b[0m')
    // 发送初始尺寸
    sendResize()
  }

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      if (msg.type === 'output') {
        term?.write(msg.data)
      }
    } catch {
      // 忽略解析错误
    }
  }

  ws.onerror = () => {
    term?.writeln('\x1b[31m✗ 终端连接失败\x1b[0m')
  }

  ws.onclose = () => {
    term?.writeln('\x1b[33m终端已断开\x1b[0m')
  }

  // 用户输入转发到后端
  term.onData((data) => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'input', data }))
    }
  })

  // 监听容器大小变化
  resizeObserver = new ResizeObserver(() => {
    fitAddon?.fit()
    sendResize()
  })
  resizeObserver.observe(terminalRef.value)
}

function sendResize() {
  if (ws?.readyState === WebSocket.OPEN && term) {
    ws.send(
      JSON.stringify({
        type: 'resize',
        cols: term.cols,
        rows: term.rows,
      }),
    )
  }
}

function disposeTerminal() {
  resizeObserver?.disconnect()
  resizeObserver = null
  ws?.close()
  ws = null
  term?.dispose()
  term = null
  fitAddon = null
}

function reconnect() {
  disposeTerminal()
  initTerminal()
}

// visible 变化时懒加载/销毁
watch(
  () => props.visible,
  (val) => {
    if (val) {
      // 等 DOM 渲染后初始化
      setTimeout(() => initTerminal(), 50)
    } else {
      disposeTerminal()
    }
  },
)

onMounted(() => {
  if (props.visible) {
    setTimeout(() => initTerminal(), 100)
  }
})

onBeforeUnmount(() => {
  disposeTerminal()
})
</script>

<template>
  <div class="terminal-panel">
    <div class="terminal-header">
      <div class="terminal-tabs">
        <span class="terminal-tab active">
          <el-icon><Monitor /></el-icon>
          Terminal
        </span>
      </div>
      <div class="terminal-actions">
        <el-tooltip content="新建终端" placement="bottom">
          <el-button text size="small" @click="reconnect">
            <el-icon><Plus /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip content="清屏" placement="bottom">
          <el-button text size="small" @click="term?.clear()">
            <el-icon><Delete /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip content="关闭面板" placement="bottom">
          <el-button text size="small" @click="closePanel">
            <el-icon><Close /></el-icon>
          </el-button>
        </el-tooltip>
      </div>
    </div>
    <div ref="terminalRef" class="terminal-container"></div>
  </div>
</template>

<style scoped>
.terminal-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #181818;
}

.terminal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px;
  height: 32px;
  background: var(--ide-bg-elevated);
  border-bottom: 1px solid var(--ide-border);
  flex-shrink: 0;
}

.terminal-tabs {
  display: flex;
  gap: 4px;
}

.terminal-tab {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  font-size: 12px;
  color: var(--ide-text-dim);
  border-bottom: 2px solid transparent;
}

.terminal-tab.active {
  color: var(--ide-text);
  border-bottom-color: var(--ide-accent);
}

.terminal-actions {
  display: flex;
  gap: 2px;
}

.terminal-actions .el-button {
  color: var(--ide-text-dim);
}
.terminal-actions .el-button:hover {
  color: var(--ide-text);
}

.terminal-container {
  flex: 1;
  padding: 4px 8px;
  overflow: hidden;
}

/* xterm 覆盖 */
.terminal-container :deep(.xterm) {
  padding: 4px;
}

.terminal-container :deep(.xterm-viewport) {
  overflow-y: auto;
}
</style>
