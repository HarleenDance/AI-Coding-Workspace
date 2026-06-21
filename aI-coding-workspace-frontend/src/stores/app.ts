import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  api,
  subscribeVibeEvents,
  type AgentConfig,
  type AgentConfigCreate,
  type FileContentResponse,
  type FileTreeNode,
  type LangGraphEvent,
  type ModelConfig,
  type ModelConfigCreate,
  type ProjectInfo,
} from '@/api'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  loading?: boolean
  error?: boolean
}

export interface VibePlan {
  threadId: string
  status: 'idle' | 'planning' | 'waiting_approval' | 'executing' | 'completed' | 'rejected'
  proposedPlan: string
  diff?: string
  feedback?: string
}

export const useAppStore = defineStore('app', () => {
  // ===== 全局 =====
  const healthOk = ref<boolean | null>(null)
  const dbVersion = ref('')

  // ===== 项目 =====
  const projects = ref<ProjectInfo[]>([])
  const currentProject = ref<ProjectInfo | null>(null)
  const projectId = ref<string>('')
  const fileTree = ref<Record<string, FileTreeNode>>({})
  const currentFile = ref<FileContentResponse | null>(null)
  const fileLoading = ref(false)
  const uploading = ref(false)

  // ===== 多 Tab =====
  const openTabs = ref<FileContentResponse[]>([])
  const activeTabPath = ref<string>('')

  // ===== 智能体 =====
  const agents = ref<AgentConfig[]>([])
  const currentAgentId = ref<string>('')
  const currentAgent = computed(() =>
    agents.value.find((a) => a.id === currentAgentId.value) || agents.value[0] || null,
  )

  // Chat 附加上下文（右键追加的代码片段）
  const chatContext = ref<string>('')

  // ===== 模型 =====
  const models = ref<ModelConfig[]>([])
  const currentModelId = ref<string>('')
  const currentModel = computed(() =>
    models.value.find((m) => m.id === currentModelId.value) ||
    models.value.find((m) => m.is_default) ||
    models.value[0] ||
    null,
  )

  // ===== 搜索 =====
  const searchQuery = ref('')
  const searchMode = ref<"keyword" | "semantic">("keyword")
  const searchResults = ref<Awaited<ReturnType<typeof api.searchCode>>["results"]>([])
  const searching = ref(false)
  const showSearch = ref(false)

  // ===== Code Chat =====
  const chatMessages = ref<ChatMessage[]>([])
  const chatLoading = ref(false)

  // ===== Vibe Coding =====
  const vibePlan = ref<VibePlan | null>(null)
  const vibeLoading = ref(false)

  // ===== SSE =====
  const sseEvents = ref<LangGraphEvent[]>([])
  const sseConnected = ref(false)
  let unsubscribeSse: (() => void) | null = null

  // ===== Actions =====

  async function checkHealth() {
    try {
      const res = await api.checkHealth()
      healthOk.value = res.status === 'ok'
      dbVersion.value = res.version
    } catch {
      healthOk.value = false
    }
  }

  async function loadProjects() {
    try {
      const res = await api.listProjects()
      projects.value = res.projects
      // 如果没有选中项目，自动选第一个
      if (!projectId.value && projects.value.length > 0) {
        await selectProject(projects.value[0].id)
      }
    } catch {
      // 忽略
    }
  }

  async function selectProject(id: string) {
    projectId.value = id
    const found = projects.value.find((p) => p.id === id)
    currentProject.value = found || null
    currentFile.value = null
    fileTree.value = {}
    openTabs.value = []
    activeTabPath.value = ''
    await loadFileTree()
  }

  async function loadFileTree() {
    if (!projectId.value) return
    try {
      const res = await api.getFileTree(projectId.value)
      fileTree.value = res.tree
    } catch {
      fileTree.value = {}
    }
  }

  async function openFile(filePath: string) {
    if (!projectId.value) return
    // 如果已经打开了，直接激活
    const existing = openTabs.value.find((t) => t.path === filePath)
    if (existing) {
      currentFile.value = existing
      activeTabPath.value = filePath
      return
    }
    fileLoading.value = true
    try {
      const file = await api.getFileContent(projectId.value, filePath)
      currentFile.value = file
      activeTabPath.value = file.path
      openTabs.value.push(file)
      if (openTabs.value.length > 8) {
        openTabs.value.shift()
      }
    } catch {
      ElMessage.error('文件加载失败')
    } finally {
      fileLoading.value = false
    }
  }

  function switchTab(filePath: string) {
    const tab = openTabs.value.find((t) => t.path === filePath)
    if (tab) {
      currentFile.value = tab
      activeTabPath.value = filePath
    }
  }

  function closeTab(filePath: string) {
    const idx = openTabs.value.findIndex((t) => t.path === filePath)
    if (idx === -1) return
    openTabs.value.splice(idx, 1)
    if (activeTabPath.value === filePath) {
      if (openTabs.value.length > 0) {
        const next = openTabs.value[Math.min(idx, openTabs.value.length - 1)]
        currentFile.value = next
        activeTabPath.value = next.path
      } else {
        currentFile.value = null
        activeTabPath.value = ''
      }
    }
  }

  async function saveFile(content: string) {
    if (!projectId.value || !currentFile.value) return
    try {
      await api.saveFile(projectId.value, currentFile.value.path, content)
      currentFile.value.content = content
      ElMessage.success('文件已保存')
    } catch {
      // 错误已在 interceptor 处理
    }
  }

  async function uploadProject(file: File) {
    uploading.value = true
    try {
      const res = await api.uploadProject(file)
      ElMessage.success(res.message)
      await loadProjects()
      await selectProject(res.id)
    } catch {
      // 错误已在 interceptor 处理
    } finally {
      uploading.value = false
    }
  }

  async function deleteProject(id: string) {
    try {
      await api.deleteProject(id)
      ElMessage.success('项目已删除')
      if (projectId.value === id) {
        projectId.value = ''
        currentProject.value = null
        fileTree.value = {}
        currentFile.value = null
      }
      await loadProjects()
    } catch {
      // 忽略
    }
  }

  const indexing = ref(false)

  async function indexProject() {
    if (!projectId.value) return
    indexing.value = true
    try {
      const res = await api.indexProject(projectId.value)
      ElMessage.success(res.message)
      await loadProjects()
    } catch {
      // 错误已在 interceptor 处理
    } finally {
      indexing.value = false
    }
  }

  async function runSearch() {
    if (!projectId.value || !searchQuery.value.trim()) return
    searching.value = true
    showSearch.value = true
    try {
      const res = await api.searchCode(
        projectId.value,
        searchQuery.value,
        searchMode.value,
      )
      searchResults.value = res.results
    } catch {
      searchResults.value = []
    } finally {
      searching.value = false
    }
  }

  function clearSearch() {
    searchQuery.value = ""
    searchResults.value = []
    showSearch.value = false
  }

  // ===== 智能体 =====
  async function loadAgents() {
    try {
      agents.value = await api.listAgents()
      if (!currentAgentId.value && agents.value.length > 0) {
        currentAgentId.value = agents.value[0].id
      }
    } catch {
      // 忽略
    }
  }

  async function createAgent(payload: AgentConfigCreate) {
    const agent = await api.createAgent(payload)
    agents.value.push(agent)
    currentAgentId.value = agent.id
    ElMessage.success('智能体已创建')
  }

  async function deleteAgent(id: string) {
    await api.deleteAgent(id)
    agents.value = agents.value.filter((a) => a.id !== id)
    if (currentAgentId.value === id) {
      currentAgentId.value = agents.value[0]?.id || ''
    }
    ElMessage.success('已删除')
  }

  /** 追加代码片段到 chat 上下文 */
  function appendCodeToContext(filePath: string, code: string) {
    const snippet = `\n\`\`\`\n// ${filePath}\n${code}\n\`\`\`\n`
    chatContext.value += snippet
  }

  function clearChatContext() {
    chatContext.value = ''
  }

  // ===== 模型 =====
  async function loadModels() {
    try {
      models.value = await api.listModels()
      if (!currentModelId.value) {
        const def = models.value.find((m) => m.is_default)
        currentModelId.value = (def || models.value[0])?.id || ''
      }
    } catch {
      // 忽略
    }
  }

  async function createModel(payload: ModelConfigCreate) {
    const model = await api.createModel(payload)
    models.value.push(model)
    if (model.is_default) {
      currentModelId.value = model.id
    }
    ElMessage.success('模型已添加')
  }

  async function deleteModel(id: string) {
    await api.deleteModel(id)
    models.value = models.value.filter((m) => m.id !== id)
    if (currentModelId.value === id) {
      const def = models.value.find((m) => m.is_default)
      currentModelId.value = (def || models.value[0])?.id || ''
    }
    ElMessage.success('已删除')
  }

  async function testModel(id: string): Promise<boolean> {
    try {
      const res = await api.testModel(id)
      if (res.ok) {
        ElMessage.success(`连通正常: ${res.reply?.slice(0, 50)}`)
      } else {
        ElMessage.error(`连通失败: ${res.error}`)
      }
      return res.ok
    } catch {
      ElMessage.error('测试失败')
      return false
    }
  }

  async function sendChat(question: string) {
    if (!projectId.value) {
      ElMessage.warning('请先选择或上传项目')
      return
    }
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question,
    }
    const assistantMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      loading: true,
    }
    // 拼接附加上下文（右键追加的代码）
    const fullQuestion = chatContext.value
      ? `${question}\n\n参考代码：\n${chatContext.value}`
      : question

    chatMessages.value.push(userMsg, assistantMsg)
    chatLoading.value = true

    // 用完后清空上下文
    chatContext.value = ''

    // 构建历史上下文（排除当前正在发送的这条）
    const history = chatMessages.value
      .filter((m) => m.id !== userMsg.id && m.id !== assistantMsg.id && !m.error)
      .map((m) => ({ role: m.role, content: m.content }))

    try {
      api.streamChat(
        {
          project_id: projectId.value,
          question: fullQuestion,
          agent_id: currentAgentId.value || undefined,
          model_id: currentModelId.value || undefined,
          history,
        },
        (data) => {
          switch (data.type) {
            case 'status':
              assistantMsg.content = data.message as string
              break
            case 'context':
              // 可选：显示检索到的文件
              break
            case 'token':
              if (assistantMsg.loading) {
                assistantMsg.loading = false
                assistantMsg.content = ''
              }
              assistantMsg.content += data.content as string
              break
            case 'error':
              assistantMsg.content = `错误：${data.message}`
              assistantMsg.error = true
              assistantMsg.loading = false
              chatLoading.value = false
              break
            case 'done':
              assistantMsg.loading = false
              chatLoading.value = false
              break
          }
        },
      )
    } catch {
      assistantMsg.content = '请求失败，请检查后端服务。'
      assistantMsg.error = true
      assistantMsg.loading = false
      chatLoading.value = false
    }
  }

  function clearChat() {
    chatMessages.value = []
  }

  async function startVibe(requirement: string) {
    if (!projectId.value) {
      ElMessage.warning('请先选择或上传项目')
      return
    }
    vibeLoading.value = true
    sseEvents.value = []
    try {
      const res = await api.startVibe({
        project_id: projectId.value,
        requirement,
      })

      vibePlan.value = {
        threadId: res.thread_id,
        status: res.status === 'waiting_approval' ? 'waiting_approval' : 'completed',
        proposedPlan: res.interrupt_payload?.proposed_plan || '',
      }

      if (vibePlan.value.status === 'waiting_approval') {
        startSse(res.thread_id)
      }
    } finally {
      vibeLoading.value = false
    }
  }

  async function confirmVibe(approved: boolean, feedback: string) {
    if (!vibePlan.value) return
    vibeLoading.value = true
    vibePlan.value.status = approved ? 'executing' : 'rejected'
    vibePlan.value.feedback = feedback

    try {
      const res = await api.confirmVibe({
        thread_id: vibePlan.value.threadId,
        approved,
        feedback,
      })

      if (approved && res.result) {
        const artifacts = (res.result as Record<string, Record<string, unknown>>)
          .generated_artifacts
        vibePlan.value.diff =
          (artifacts?.diff as string) || (artifacts?.['diff'] as string) || ''
        vibePlan.value.status = 'completed'
      }
    } finally {
      vibeLoading.value = false
      stopSse()
    }
  }

  function resetVibe() {
    vibePlan.value = null
    sseEvents.value = []
    stopSse()
  }

  async function applyVibeDiff() {
    if (!vibePlan.value?.diff || !projectId.value) return
    vibeLoading.value = true
    try {
      const res = await api.applyVibeDiff({
        project_id: projectId.value,
        diff: vibePlan.value.diff,
      })
      ElMessage.success(res.message)
      // 刷新文件树
      await loadFileTree()
    } catch {
      // 错误已在 interceptor 处理
    } finally {
      vibeLoading.value = false
    }
  }

  function startSse(threadId: string) {
    stopSse()
    sseConnected.value = true
    unsubscribeSse = subscribeVibeEvents(
      threadId,
      (event) => {
        sseEvents.value.push(event as LangGraphEvent)
        if (sseEvents.value.length > 200) {
          sseEvents.value = sseEvents.value.slice(-200)
        }
      },
      () => {
        sseConnected.value = false
      },
    )
  }

  function stopSse() {
    if (unsubscribeSse) {
      unsubscribeSse()
      unsubscribeSse = null
    }
    sseConnected.value = false
  }

  return {
    // state
    healthOk,
    dbVersion,
    projects,
    currentProject,
    projectId,
    fileTree,
    currentFile,
    fileLoading,
    uploading,
    indexing,
    openTabs,
    activeTabPath,
    chatMessages,
    chatLoading,
    vibePlan,
    vibeLoading,
    sseEvents,
    sseConnected,
    searchQuery,
    searchMode,
    searchResults,
    searching,
    showSearch,
    agents,
    currentAgentId,
    currentAgent,
    chatContext,
    models,
    currentModelId,
    currentModel,
    // actions
    checkHealth,
    loadProjects,
    selectProject,
    loadFileTree,
    openFile,
    switchTab,
    closeTab,
    saveFile,
    uploadProject,
    deleteProject,
    indexProject,
    runSearch,
    clearSearch,
    loadAgents,
    createAgent,
    deleteAgent,
    appendCodeToContext,
    clearChatContext,
    loadModels,
    createModel,
    deleteModel,
    testModel,
    sendChat,
    clearChat,
    startVibe,
    confirmVibe,
    resetVibe,
    applyVibeDiff,
  }
})
