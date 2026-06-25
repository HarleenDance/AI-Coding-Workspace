<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as monaco from 'monaco-editor'
import { api } from '@/api'
import { useAppStore } from '@/stores/app'

interface Props {
  /** 普通代码模式：显示的代码内容 */
  code?: string
  language?: string
  /** Diff 模式：原始内容 */
  original?: string
  /** Diff 模式：修改后内容 */
  modified?: string
  readOnly?: boolean
  /** 当前文件路径（用于补全上下文） */
  filePath?: string
}

const props = withDefaults(defineProps<Props>(), {
  code: '',
  language: 'plaintext',
  readOnly: true,
  filePath: '',
})

const emit = defineEmits<{
  change: [content: string]
  append: [code: string]
}>()

const isDiff = computed(() => props.original !== undefined && props.modified !== undefined)

const containerRef = ref<HTMLDivElement>()
let editor: monaco.editor.IStandaloneCodeEditor | monaco.editor.IStandaloneDiffEditor | null = null

// ===== AI 代码补全 =====
const store = useAppStore()
let completionProvider: monaco.IDisposable | null = null
let inlineCompletionProvider: monaco.IDisposable | null = null
let lastRequestKey = '' // 去重：同一位置短时间不重复请求

function setupCompletionProvider() {
  if (inlineCompletionProvider) return

  inlineCompletionProvider = monaco.languages.registerInlineCompletionsProvider(
    { pattern: '**' },
    {
      async provideInlineCompletions(model, position, context, token) {
        // 只对可编辑的编辑器生效
        if (props.readOnly || isDiff.value) return { items: [] }

        const lineContent = model.getLineContent(position.lineNumber)
        const textBeforeCursor = lineContent.substring(0, position.column - 1)

        // 触发条件：光标前有内容且以这些字符结尾，或手动触发
        const triggerChars = ['.', ' ', '(', '=', ':', '\t', "'", '"', ',']
        const shouldTrigger =
          context.triggerKind === monaco.languages.InlineCompletionTriggerKind.Automatic
            ? textBeforeCursor.length > 0 &&
              triggerChars.some((c) => textBeforeCursor.endsWith(c)) &&
              textBeforeCursor.trim().length > 1
            : true

        if (!shouldTrigger) return { items: [] }

        const fullText = model.getValue()
        const offset = model.getOffsetAt(position)
        const prefix = fullText.substring(0, offset)
        const suffix = fullText.substring(offset)

        // 去重：避免相同上下文频繁请求
        const requestKey = `${props.filePath}:${offset}:${textBeforeCursor.slice(-20)}`
        if (requestKey === lastRequestKey) return { items: [] }
        lastRequestKey = requestKey

        try {
          const res = await api.completeCode({
            prefix,
            suffix,
            language: props.language,
            file_path: props.filePath,
            model_id: store.currentModelId || undefined,
            temperature: 0.2,
            max_tokens: 128,
          })

          if (token.isCancellationRequested || !res.text?.trim()) {
            return { items: [] }
          }

          return {
            items: [
              {
                insertText: res.text,
                range: {
                  startLineNumber: position.lineNumber,
                  startColumn: position.column,
                  endLineNumber: position.lineNumber,
                  endColumn: position.column,
                },
              },
            ],
          }
        } catch {
          return { items: [] }
        }
      },
      freeInlineCompletions() {},
    },
  )
}

function disposeCompletionProvider() {
  inlineCompletionProvider?.dispose()
  inlineCompletionProvider = null
}

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
      // 启用 inline suggestions（AI 补全幽灵文本）
      'inlineSuggest.enabled': true,
      quickSuggestions: { other: true, comments: false, strings: false },
      suggestOnTriggerCharacters: true,
      tabCompletion: 'on',
      wordBasedSuggestions: 'off',
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

    // 添加手动触发 AI 补全的快捷键：Alt + \
    codeEditor.addAction({
      id: 'trigger-ai-completion',
      label: '触发 AI 代码补全',
      keybindings: [monaco.KeyMod.Alt | monaco.KeyCode.Backslash],
      run: (ed) => {
        // 通过临时修改内容触发 inline suggest
        const position = ed.getPosition()
        if (position) {
          // 使用官方命令触发
          ed.trigger('ai-completion', 'editor.action.inlineSuggest.trigger', {})
        }
      },
    })

    // 注册 AI 补全 provider（只注册一次）
    setupCompletionProvider()
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
  disposeCompletionProvider()
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
