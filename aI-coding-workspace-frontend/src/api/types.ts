// 与后端 schemas 对齐的类型定义

export interface HealthResponse {
  status: string
  database: string
  version: string
}

// ===== 模型相关 =====

export interface ModelConfig {
  id: string
  name: string
  provider: string
  base_url: string
  api_key: string
  api_key_masked: string
  chat_model: string
  reasoner_model: string
  temperature: number
  max_tokens: number
  is_builtin: boolean
  is_active: boolean
  is_default: boolean
}

export interface ModelConfigCreate {
  name: string
  provider: string
  base_url: string
  api_key: string
  chat_model: string
  reasoner_model?: string
  temperature?: number
  max_tokens?: number
  is_default?: boolean
}

export interface ModelConfigUpdate {
  name?: string
  base_url?: string
  api_key?: string
  chat_model?: string
  reasoner_model?: string
  temperature?: number
  max_tokens?: number
  is_active?: boolean
  is_default?: boolean
}

// ===== 智能体相关 =====

export interface AgentConfig {
  id: string
  name: string
  description: string
  avatar: string
  system_prompt: string
  temperature: number
  model_route: string
  tools: string[]
  is_builtin: boolean
  is_active: boolean
}

export interface AgentConfigCreate {
  name: string
  description?: string
  avatar?: string
  system_prompt: string
  temperature?: number
  model_route?: string
  tools?: string[]
}

export interface AgentConfigUpdate {
  name?: string
  description?: string
  avatar?: string
  system_prompt?: string
  temperature?: number
  model_route?: string
  tools?: string[]
  is_active?: boolean
}

// ===== 项目相关 =====

export interface ProjectInfo {
  id: string
  name: string
  description: string | null
  is_indexed: boolean
  file_count: number
  created_at: string | null
}

export interface ProjectListResponse {
  projects: ProjectInfo[]
}

export interface UploadResponse {
  id: string
  name: string
  file_count: number
  message: string
}

export interface FileTreeNode {
  _type: 'dir' | 'file'
  _path?: string
  _language?: string
  _size?: number
  _children?: Record<string, FileTreeNode>
}

export interface FileTreeResponse {
  project_id: string
  tree: Record<string, FileTreeNode>
}

export interface FileContentResponse {
  path: string
  language: string
  size: number
  content: string
}

export interface ChatRequest {
  project_id: string
  question: string
}

export interface ChatResponse {
  answer: string
  artifacts: Record<string, unknown>
}

export interface VibeStartRequest {
  project_id: string
  requirement: string
}

export interface VibeInterruptPayload {
  type?: string
  thread_id?: string
  project_id?: string
  proposed_plan?: string
}

export interface VibeStartResponse {
  thread_id: string
  status: string
  interrupt_payload: VibeInterruptPayload | null
}

export interface VibeConfirmRequest {
  thread_id: string
  approved: boolean
  feedback: string
}

export interface VibeConfirmResponse {
  thread_id: string
  status: string
  result: Record<string, unknown> | null
}

export interface HarnessRun {
  command: string
  passed: boolean
  return_code: number
  stdout: string
  stderr: string
}

export interface HarnessResult {
  passed: boolean
  commands: string[]
  runs: HarnessRun[]
  summary?: string
  error?: string
  diff_apply?: Record<string, unknown>
}

export interface ReviewFinding {
  severity: 'blocker' | 'major' | 'minor' | string
  dimension: string
  message: string
}

export interface ReviewReport {
  passed: boolean
  summary: string
  findings: ReviewFinding[]
  raw?: string
}

export interface VibeApplyRequest {
  project_id: string
  diff: string
}

export interface VibeApplyResponse {
  applied_files: string[]
  message: string
}

// SSE 事件（LangGraph astream_events v2）
export interface LangGraphEvent {
  event: string
  name?: string
  data?: unknown
  tags?: string[]
  run_id?: string
  metadata?: Record<string, unknown>
}
