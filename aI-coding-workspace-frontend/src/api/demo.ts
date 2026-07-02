import type {
  AxiosResponse,
  InternalAxiosRequestConfig,
} from 'axios'

type DemoFile = {
  language: string
  content: string
}

const projectId = 'demo-project-xiaochi'
const now = '2026-07-02T10:00:00+08:00'

export function isStaticDemo(): boolean {
  return (
    import.meta.env.VITE_STATIC_DEMO === 'true' ||
    globalThis.location?.hostname.endsWith('github.io')
  )
}

const demoFiles: Record<string, DemoFile> = {
  'app/engine/workflow.py': {
    language: 'python',
    content: `from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt

from app.engine.agents import router_agent, planner_agent, coder_agent
from app.engine.agents import tester_agent, reviewer_agent
from app.engine.state import GraphState


def human_approval_node(state: GraphState):
    approval = interrupt({
        "type": "sdd_plan_approval",
        "proposed_plan": state["proposed_plan"],
    })
    return {"human_approved": approval["approved"]}


def build_workflow():
    builder = StateGraph(GraphState)
    builder.add_node("router_agent", router_agent)
    builder.add_node("planner_agent", planner_agent)
    builder.add_node("human_approval_node", human_approval_node)
    builder.add_node("coder_agent", coder_agent)
    builder.add_node("tester_agent", tester_agent)
    builder.add_node("reviewer_agent", reviewer_agent)
    builder.add_edge(START, "router_agent")
    return builder
`,
  },
  'app/engine/context/manager.py': {
    language: 'python',
    content: `from dataclasses import dataclass

@dataclass(frozen=True)
class ContextBudget:
    total_chars: int = 48000
    history_chars: int = 10000
    code_chars: int = 26000
    per_file_chars: int = 5000


def render_code_context(context_files, budget=ContextBudget()):
    """Render retrieved code with dedupe, per-file caps, and total budget caps."""
    seen = set()
    rendered = []
    for item in context_files:
        key = (item["file_path"], item["content"])
        if key in seen:
            continue
        seen.add(key)
        rendered.append(item)
    return rendered
`,
  },
  'app/engine/harness.py': {
    language: 'python',
    content: `def discover_harness_commands(project_root):
    if (project_root / "harness.json").exists():
        return load_harness_config(project_root / "harness.json")
    if (project_root / "package.json").exists():
        return ["npm test", "npm run build"]
    if (project_root / "pyproject.toml").exists():
        return ["python -m pytest"]
    return []


def run_harness(project_root, diff_text):
    """Apply generated diff in a temp workspace and run tests."""
    commands = discover_harness_commands(project_root)
    runs = [run_command(command) for command in commands]
    return {"passed": all(run["passed"] for run in runs), "runs": runs}
`,
  },
  'src/components/VibeTab.vue': {
    language: 'vue',
    content: `<script setup lang="ts">
import { ref } from 'vue'
import { useAppStore } from '@/stores/app'

const store = useAppStore()
const requirement = ref('')

function start() {
  store.startVibe(requirement.value)
}
</script>

<template>
  <section class="vibe-panel">
    <textarea v-model="requirement" />
    <button @click="start">生成 SDD 方案</button>
  </section>
</template>
`,
  },
}

const fileTree = {
  app: {
    _type: 'dir',
    _children: {
      engine: {
        _type: 'dir',
        _children: {
          'workflow.py': { _type: 'file', _path: 'app/engine/workflow.py', _language: 'python', _size: 920 },
          context: {
            _type: 'dir',
            _children: {
              'manager.py': { _type: 'file', _path: 'app/engine/context/manager.py', _language: 'python', _size: 760 },
            },
          },
          'harness.py': { _type: 'file', _path: 'app/engine/harness.py', _language: 'python', _size: 620 },
        },
      },
    },
  },
  src: {
    _type: 'dir',
    _children: {
      components: {
        _type: 'dir',
        _children: {
          'VibeTab.vue': { _type: 'file', _path: 'src/components/VibeTab.vue', _language: 'vue', _size: 460 },
        },
      },
    },
  },
}

function ok<T>(config: InternalAxiosRequestConfig, data: T): AxiosResponse<T> {
  return {
    data,
    status: 200,
    statusText: 'OK',
    headers: {},
    config,
  }
}

function notFound(config: InternalAxiosRequestConfig): AxiosResponse {
  return ok(config, { detail: 'Demo data not found' })
}

function readBody(config: InternalAxiosRequestConfig): Record<string, unknown> {
  if (!config.data) return {}
  if (typeof config.data === 'string') {
    try {
      return JSON.parse(config.data)
    } catch {
      return {}
    }
  }
  return config.data as Record<string, unknown>
}

export async function demoAdapter(config: InternalAxiosRequestConfig): Promise<AxiosResponse> {
  const method = (config.method || 'get').toUpperCase()
  const url = config.url || ''
  const body = readBody(config)

  if (method === 'GET' && url === '/health/db') {
    return ok(config, {
      status: 'ok',
      database: 'static-demo',
      version: 'GitHub Pages Demo',
    })
  }

  if (method === 'GET' && url === '/projects') {
    return ok(config, {
      projects: [
        {
          id: projectId,
          name: '小翅 AI Coding Workflow 平台',
          description: '企业级 AI 编码治理与研发工作流演示项目',
          is_indexed: true,
          file_count: Object.keys(demoFiles).length,
          created_at: now,
        },
      ],
    })
  }

  if (method === 'GET' && url === `/projects/${projectId}/files`) {
    return ok(config, { project_id: projectId, tree: fileTree })
  }

  if (method === 'GET' && url === `/projects/${projectId}/file`) {
    const path = String(config.params?.path || '')
    const file = demoFiles[path]
    if (!file) return notFound(config)
    return ok(config, {
      path,
      language: file.language,
      size: file.content.length,
      content: file.content,
    })
  }

  if (method === 'POST' && url === `/projects/${projectId}/search`) {
    const query = String(body.query || 'Agent')
    return ok(config, {
      query,
      mode: body.mode || 'semantic',
      results: Object.entries(demoFiles).slice(0, 4).map(([filePath, file], index) => ({
        file_path: filePath,
        content: file.content.slice(0, 680),
        symbol: index === 0 ? 'build_workflow' : null,
        start_line: 1,
        end_line: Math.min(file.content.split('\n').length, 40),
        score: Number((0.92 - index * 0.07).toFixed(2)),
        match_count: 3 - Math.min(index, 2),
      })),
    })
  }

  if (method === 'GET' && url === '/agents') {
    return ok(config, [
      {
        id: 'agent-planner',
        name: 'SDD Planner',
        description: '根据需求、规范和代码上下文生成实施方案',
        avatar: 'Route',
        system_prompt: '你是企业级 SDD 方案规划 Agent。',
        temperature: 0.2,
        model_route: 'reasoner',
        tools: ['code_rag', 'sdd_policy'],
        is_builtin: true,
        is_active: true,
      },
      {
        id: 'agent-reviewer',
        name: 'AI Reviewer',
        description: '从规范、性能、安全维度审查生成 diff',
        avatar: 'ShieldCheck',
        system_prompt: '你是代码审查 Agent。',
        temperature: 0.1,
        model_route: 'chat',
        tools: ['harness_result', 'code_rag'],
        is_builtin: true,
        is_active: true,
      },
    ])
  }

  if (method === 'GET' && url === '/models') {
    return ok(config, [
      {
        id: 'model-demo',
        name: 'Demo Model',
        provider: 'static',
        base_url: 'https://demo.local',
        api_key: '',
        api_key_masked: 'demo',
        chat_model: 'demo-chat',
        reasoner_model: 'demo-reasoner',
        temperature: 0.2,
        max_tokens: 4096,
        is_builtin: true,
        is_active: true,
        is_default: true,
      },
    ])
  }

  if (method === 'POST' && url === '/vibe/start') {
    return ok(config, {
      thread_id: 'demo-thread-001',
      status: 'waiting_approval',
      interrupt_payload: {
        type: 'sdd_plan_approval',
        thread_id: 'demo-thread-001',
        project_id: projectId,
        proposed_plan: `# SDD 实施方案

## 需求目标
基于用户需求生成可审查、可测试、可追溯的代码变更。

## 工作流
1. Router 识别任务类型。
2. Planner 生成 SDD 方案和验收标准。
3. Coder 输出最小 unified diff。
4. Tester 调用 Harness 执行单元测试与集成测试。
5. Reviewer 从规范、性能、安全维度审查。

## 验收标准
- Harness 测试通过。
- Reviewer 无阻断级问题。
- 变更范围与 SDD 方案一致。`,
      },
    })
  }

  if (method === 'POST' && url === '/vibe/confirm') {
    return ok(config, {
      thread_id: body.thread_id || 'demo-thread-001',
      status: body.approved ? 'completed' : 'rejected',
      result: {
        retry_count: 1,
        generated_artifacts: {
          diff: `diff --git a/app/engine/context/manager.py b/app/engine/context/manager.py
--- a/app/engine/context/manager.py
+++ b/app/engine/context/manager.py
@@
+class ContextBudget:
+    total_chars = 48000
+    code_chars = 26000`,
          harness: {
            passed: true,
            commands: ['python -m pytest', 'npm run build'],
            runs: [
              { command: 'python -m pytest', passed: true, return_code: 0, stdout: '18 passed', stderr: '' },
              { command: 'npm run build', passed: true, return_code: 0, stdout: 'vite build completed', stderr: '' },
            ],
            summary: 'Harness 测试全部通过，未发现回归。',
          },
          review: {
            passed: true,
            summary: '代码变更范围可控，符合 SDD 方案，未发现阻断级问题。',
            findings: [
              { severity: 'minor', dimension: 'maintainability', message: '建议后续接入 tokenizer 进行更精确预算。' },
            ],
          },
        },
      },
    })
  }

  if (method === 'GET' && url === `/vibe/history/${projectId}`) {
    return ok(config, {
      tasks: [
        {
          id: 'task-001',
          thread_id: 'demo-thread-001',
          task_type: 'vibe_coding',
          status: 'completed',
          requirement: '为 AI Coding Agent 增加上下文预算和 Harness 测试闭环',
          created_at: now,
          updated_at: now,
        },
      ],
    })
  }

  if (method === 'POST' && url === '/vibe/apply') {
    return ok(config, {
      applied_files: ['app/engine/context/manager.py'],
      message: 'Demo 模式：已模拟应用 1 个文件变更。',
    })
  }

  if (method === 'POST' && url === '/completion') {
    return ok(config, {
      text: '  # Demo completion: add focused tests before merging\\n',
      stop: true,
    })
  }

  if (method === 'POST' && url.endsWith('/index')) {
    return ok(config, { message: 'Demo 模式：项目索引已刷新。', indexed_count: 42 })
  }

  if (method === 'PUT' && url.includes('/file')) {
    return ok(config, { message: 'Demo 模式：文件已保存。' })
  }

  return ok(config, { message: 'Demo 模式：该接口已模拟返回。' })
}

export function streamDemoChat(
  payload: { question: string },
  onEvent: (data: { type: string; [key: string]: unknown }) => void,
): AbortController {
  const controller = new AbortController()
  const answer = `这是 GitHub Pages 静态演示模式。针对“${payload.question}”，平台会先通过 Code RAG 检索相关代码，再用 Context Budget 控制系统指令、历史对话和代码片段预算，最后结合 SDD、Harness 和 Reviewer 输出可审查的研发建议。`
  const events = [
    { type: 'status', message: '正在检索代码上下文...' },
    {
      type: 'context',
      files: ['app/engine/workflow.py', 'app/engine/context/manager.py', 'app/engine/harness.py'],
      budget: {
        total_chars: 18420,
        total_budget_chars: 48000,
        included_files: 3,
        trimmed_files: 1,
        kept_history_items: 4,
      },
    },
    { type: 'status', message: 'AI 思考中...' },
    ...answer.match(/.{1,18}/g)!.map((content) => ({ type: 'token', content })),
    { type: 'done', answer },
  ]

  events.forEach((event, index) => {
    globalThis.setTimeout(() => {
      if (!controller.signal.aborted) onEvent(event)
    }, index * 90)
  })

  return controller
}

export function subscribeDemoVibeEvents(
  onEvent: (event: unknown) => void,
): () => void {
  const timers = [
    { event: 'on_chain_start', name: 'router_agent' },
    { event: 'on_chain_end', name: 'planner_agent' },
    { event: 'on_chain_start', name: 'tester_agent' },
    { event: 'on_chain_end', name: 'reviewer_agent' },
  ].map((event, index) =>
    globalThis.setTimeout(() => onEvent(event), index * 550),
  )
  return () => timers.forEach((timer) => globalThis.clearTimeout(timer))
}
