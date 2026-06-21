<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as monaco from 'monaco-editor'

interface Props {
  /** 普通代码模式：显示的代码内容 */
  code?: string
  language?: string
  /** Diff 模式：原始内容 */
  original?: string
  /** Diff 模式：修改后内容 */
  modified?: string
  readOnly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  code: '',
  language: 'plaintext',
  readOnly: true,
})

const emit = defineEmits<{
  change: [content: string]
  append: [code: string]
}>()

const isDiff = computed(() => props.original !== undefined && props.modified !== undefined)

const containerRef = ref<HTMLDivElement>()
let editor: monaco.editor.IStandaloneCodeEditor | monaco.editor.IStandaloneDiffEditor | null = null

function defineTheme() {
  monaco.editor.defineTheme('ide-dark', {
    base: 'vs-dark',
    inherit: true,
    rules: [],
    colors: {
      'editor.background': '#1e1e2e',
      'editor.lineHighlightBackground': '#2a2a3e',
      'editorLineNumber.foreground': '#585b70',
      'editorLineNumber.activeForeground': '#cdd6f4',
      'editor.selectionBackground': '#585b7055',
      'diffEditor.insertedTextBackground': '#a6e3a122',
      'diffEditor.removedTextBackground': '#f38ba822',
    },
  })
}

function createEditor() {
  if (!containerRef.value) return
  defineTheme()

  if (isDiff.value) {
    editor = monaco.editor.createDiffEditor(containerRef.value, {
      theme: 'ide-dark',
      readOnly: props.readOnly,
      automaticLayout: true,
      fontSize: 13,
      fontFamily: "JetBrains Mono, Consolas, monospace",
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      renderSideBySide: true,
    })
    ;(editor as monaco.editor.IStandaloneDiffEditor).setModel({
      original: monaco.editor.createModel(props.original || '', props.language),
      modified: monaco.editor.createModel(props.modified || '', props.language),
    })
  } else {
    editor = monaco.editor.create(containerRef.value, {
      theme: 'ide-dark',
      value: props.code,
      language: props.language,
      readOnly: props.readOnly,
      automaticLayout: true,
      fontSize: 13,
      fontFamily: "JetBrains Mono, Consolas, monospace",
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      lineNumbers: 'on',
      folding: true,
      wordWrap: 'on',
    })
    // 监听内容变更（编辑模式）
    if (!props.readOnly) {
      const codeEditor = editor as monaco.editor.IStandaloneCodeEditor
      codeEditor.onDidChangeModelContent(() => {
        emit('change', codeEditor.getValue())
      })
    }

    // 右键菜单：追加选中代码到对话框
    const codeEditor = editor as monaco.editor.IStandaloneCodeEditor
    codeEditor.addAction({
      id: 'append-to-chat',
      label: '追加到 AI 对话框',
      keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyM],
      contextMenuGroupId: '9_ai',
      contextMenuOrder: 1,
      run: (ed) => {
        const selection = ed.getSelection()
        const model = ed.getModel()
        if (selection && model) {
          const selectedText = model.getValueInRange(selection)
          if (selectedText) {
            emit('append', selectedText)
          }
        }
      },
    })

    // 右键菜单：追加整个文件
    codeEditor.addAction({
      id: 'append-file-to-chat',
      label: '追加整个文件到 AI 对话框',
      contextMenuGroupId: '9_ai',
      contextMenuOrder: 2,
      run: (ed) => {
        const model = ed.getModel()
        if (model) {
          emit('append', model.getValue())
        }
      },
    })
  }
}

function disposeEditor() {
  if (editor) {
    editor.dispose()
    editor = null
  }
}

onMounted(() => {
  createEditor()
})

onBeforeUnmount(() => {
  disposeEditor()
})

// 内容变化时重建（简化处理）
watch(
  () => [props.code, props.original, props.modified, props.language],
  () => {
    disposeEditor()
    createEditor()
  },
)
</script>

<template>
  <div ref="containerRef" class="monaco-container"></div>
</template>

<style scoped>
.monaco-container {
  width: 100%;
  height: 100%;
}
</style>
