import http from './http'
import type {
  AgentConfig,
  AgentConfigCreate,
  AgentConfigUpdate,
  ChatRequest,
  ChatResponse,
  FileContentResponse,
  FileTreeResponse,
  HealthResponse,
  ModelConfig,
  ModelConfigCreate,
  ModelConfigUpdate,
  ProjectListResponse,
  UploadResponse,
  VibeApplyRequest,
  VibeApplyResponse,
  VibeConfirmRequest,
  VibeConfirmResponse,
  VibeStartRequest,
  VibeStartResponse,
} from './types'

export * from './types'

export const api = {
  /** 通用 GET（带完整路径，已含 query） */
  httpGet<T>(url: string): Promise<T> {
    return http.get<T>(url).then((r) => r.data)
  },

  /** 通用 POST */
  httpPost<T = unknown>(url: string, body: unknown): Promise<T> {
    return http.post<T>(url, body).then((r) => r.data)
  },

  checkHealth(): Promise<HealthResponse> {
    return http.get<HealthResponse>('/health/db').then((r) => r.data)
  },

  // ===== 模型 =====
  listModels(): Promise<ModelConfig[]> {
    return http.get<ModelConfig[]>('/models').then((r) => r.data)
  },

  createModel(payload: ModelConfigCreate): Promise<ModelConfig> {
    return http.post<ModelConfig>('/models', payload).then((r) => r.data)
  },

  updateModel(id: string, payload: ModelConfigUpdate): Promise<ModelConfig> {
    return http.put<ModelConfig>(`/models/${id}`, payload).then((r) => r.data)
  },

  deleteModel(id: string): Promise<{ message: string }> {
    return http.delete(`/models/${id}`).then((r) => r.data)
  },

  initBuiltinModels(): Promise<{ message: string; created: number }> {
    return http.post('/models/init-builtin').then((r) => r.data)
  },

  testModel(id: string): Promise<{ ok: boolean; reply?: string; error?: string }> {
    return http.post(`/models/${id}/test`).then((r) => r.data)
  },

  // ===== 智能体 =====
  listAgents(): Promise<AgentConfig[]> {
    return http.get<AgentConfig[]>('/agents').then((r) => r.data)
  },

  createAgent(payload: AgentConfigCreate): Promise<AgentConfig> {
    return http.post<AgentConfig>('/agents', payload).then((r) => r.data)
  },

  updateAgent(id: string, payload: AgentConfigUpdate): Promise<AgentConfig> {
    return http.put<AgentConfig>(`/agents/${id}`, payload).then((r) => r.data)
  },

  deleteAgent(id: string): Promise<{ message: string }> {
    return http.delete(`/agents/${id}`).then((r) => r.data)
  },

  initBuiltinAgents(): Promise<{ message: string; created: number }> {
    return http.post('/agents/init-builtin').then((r) => r.data)
  },

  // ===== 项目 =====
  listProjects(): Promise<ProjectListResponse> {
    return http.get<ProjectListResponse>('/projects').then((r) => r.data)
  },

  uploadProject(file: File): Promise<UploadResponse> {
    const formData = new FormData()
    formData.append('file', file)
    return http
      .post<UploadResponse>('/projects/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 300_000, // 上传+解压+索引可能较慢
      })
      .then((r) => r.data)
  },

  /**
   * 上传文件夹（多文件，保留目录结构）。
   * 利用 webkitdirectory 获取每个文件的 webkitRelativePath。
   */
  uploadFolder(files: File[], folderName: string): Promise<UploadResponse> {
    const formData = new FormData()
    for (const f of files) {
      // 用 webkitRelativePath 作为路径，通过 header 传给后端
      const relPath = (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name
      formData.append('files', f, relPath)
    }
    formData.append('folder_name', folderName)
    return http
      .post<UploadResponse>('/projects/upload-folder', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 300_000,
      })
      .then((r) => r.data)
  },

  getFileTree(projectId: string): Promise<FileTreeResponse> {
    return http
      .get<FileTreeResponse>(`/projects/${projectId}/files`)
      .then((r) => r.data)
  },

  getFileContent(projectId: string, filePath: string): Promise<FileContentResponse> {
    return http
      .get<FileContentResponse>(`/projects/${projectId}/file`, {
        params: { path: filePath },
      })
      .then((r) => r.data)
  },

  saveFile(projectId: string, filePath: string, content: string): Promise<{ message: string }> {
    return http
      .put(
        `/projects/${projectId}/file`,
        { content },
        { params: { path: filePath } },
      )
      .then((r) => r.data)
  },

  deleteProject(projectId: string): Promise<{ message: string }> {
    return http.delete(`/projects/${projectId}`).then((r) => r.data)
  },

  indexProject(
    projectId: string,
  ): Promise<{ message: string; indexed_count: number }> {
    return http
      .post(`/projects/${projectId}/index`, {}, { timeout: 300_000 })
      .then((r) => r.data)
  },

  // ===== Chat =====
  chat(payload: ChatRequest): Promise<ChatResponse> {
    return http.post<ChatResponse>('/chat', payload).then((r) => r.data)
  },

  /**
   * 流式 Chat（SSE）。
   * @param payload 请求体（含 history）
   * @param onEvent 收到 SSE 事件的回调
   * @returns AbortController（用于取消）
   */
  streamChat(
    payload: {
      project_id: string
      question: string
      history: { role: string; content: string }[]
      agent_id?: string
      model_id?: string
    },
    onEvent: (data: { type: string; [key: string]: unknown }) => void,
  ): AbortController {
    const controller = new AbortController()

    const run = async () => {
      try {
        const resp = await fetch('/api/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          signal: controller.signal,
        })
        if (!resp.ok || !resp.body) {
          onEvent({ type: 'error', message: `HTTP ${resp.status}` })
          return
        }
        const reader = resp.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })

          const parts = buffer.split('\n\n')
          buffer = parts.pop() ?? ''

          for (const part of parts) {
            const dataLines = part
              .split('\n')
              .filter((l) => l.startsWith('data:'))
              .map((l) => l.slice(5).trim())
              .join('')
            if (dataLines) {
              try {
                onEvent(JSON.parse(dataLines))
              } catch {
                // 忽略非 JSON
              }
            }
          }
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          onEvent({ type: 'error', message: String(err) })
        }
      }
    }

    run()
    return controller
  },

  // ===== Vibe =====
  startVibe(payload: VibeStartRequest): Promise<VibeStartResponse> {
    return http.post<VibeStartResponse>('/vibe/start', payload).then((r) => r.data)
  },

  confirmVibe(payload: VibeConfirmRequest): Promise<VibeConfirmResponse> {
    return http
      .post<VibeConfirmResponse>('/vibe/confirm', payload)
      .then((r) => r.data)
  },

  applyVibeDiff(payload: VibeApplyRequest): Promise<VibeApplyResponse> {
    return http.post<VibeApplyResponse>('/vibe/apply', payload).then((r) => r.data)
  },

  getVibeHistory(projectId: string): Promise<{
    tasks: {
      id: string
      thread_id: string
      task_type: string
      status: string
      requirement: string
      created_at: string | null
      updated_at: string | null
    }[]
  }> {
    return http.get(`/vibe/history/${projectId}`).then((r) => r.data)
  },

  searchCode(
    projectId: string,
    query: string,
    mode: "keyword" | "semantic",
  ): Promise<{
    query: string
    mode: string
    results: {
      file_path: string
      content: string
      symbol: string | null
      start_line: number
      end_line: number
      score: number
      match_count?: number
    }[]
  }> {
    return http
      .post(`/projects/${projectId}/search`, { query, mode }, { timeout: 60_000 })
      .then((r) => r.data)
  },

  /**
   * AI 代码补全（非流式）。
   */
  completeCode(payload: {
    prefix: string
    suffix: string
    language: string
    file_path: string
    model_id?: string
    temperature?: number
    max_tokens?: number
  }): Promise<{ text: string; stop: boolean }> {
    return http
      .post<{ text: string; stop: boolean }>('/completion', payload, {
        timeout: 20_000,
      })
      .then((r) => r.data)
  },
}

/**
 * 订阅 Vibe Coding 的 SSE 事件流。
 * 返回一个关闭函数。
 */
export function subscribeVibeEvents(
  threadId: string,
  onEvent: (event: unknown) => void,
  onError?: (err: unknown) => void,
): () => void {
  // 使用 fetch 处理 SSE，以便手动解析 text/event-stream
  const controller = new AbortController()

  const run = async () => {
    try {
      const resp = await fetch(`/api/vibe/${threadId}/events`, {
        signal: controller.signal,
        headers: { Accept: 'text/event-stream' },
      })
      if (!resp.ok || !resp.body) {
        onError?.(new Error(`SSE 连接失败: ${resp.status}`))
        return
      }
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        // 按 SSE 事件边界（双换行）拆分
        const parts = buffer.split('\n\n')
        buffer = parts.pop() ?? ''

        for (const part of parts) {
          const dataLine = part
            .split('\n')
            .filter((l) => l.startsWith('data:'))
            .map((l) => l.slice(5).trim())
            .join('\n')
          if (dataLine) {
            try {
              onEvent(JSON.parse(dataLine))
            } catch {
              // 非 JSON 数据忽略
            }
          }
        }
      }
    } catch (err) {
      if (!controller.signal.aborted) {
        onError?.(err)
      }
    }
  }

  run()

  return () => controller.abort()
}
