# AI Coding Workspace Agent 架构深挖审计

> 审计目标：围绕 Context/Memory、Human-in-the-loop、Evaluation、Tool Retrieval、Streaming 五个维度，定位当前实现、识别缺口，并沉淀成可落地的 PR 方向与面试叙事材料。

## 3. Context / Memory 管理

**现状描述：**

- `aI-coding-workspace-backend/app/api/v1/endpoints/chat.py::chat_stream` 会先调用 `retrieve_code_context()` 检索代码片段，再把所有 `context_files` 直接拼接成 `context_text` 放入当前 user message。
- `aI-coding-workspace-backend/app/api/v1/endpoints/chat.py::chat_stream` 只保留 `payload.history[-10:]`，属于固定轮数滚动窗口。
- `aI-coding-workspace-frontend/src/stores/app.ts::sendChat` 从前端内存里的 `chatMessages` 拼接历史，发送给后端；刷新页面后普通 Chat 历史会丢失。
- `aI-coding-workspace-backend/app/engine/agents/planner.py::_context_text`、`coder.py::_context_text`、`qa.py::qa_agent` 同样直接 join 检索结果，没有 token budget、去重、摘要或优先级排序。
- `aI-coding-workspace-backend/app/engine/agents/multi_model.py::build_chat_model` 的 `max_tokens` 控制的是模型输出长度，不是输入 context 的预算管理。
- Vibe Coding 的任务结果会存入 `AgentTask.output_payload`，LangGraph checkpoint 存在 `runtime/langgraph_checkpoints.sqlite3`，但普通 Chat 没有服务端持久化会话表。

**缺陷 / 缺失：**

- 当前策略是“固定 10 轮历史 + 全量拼接 RAG 片段”，不是严格的硬截断、滚动摘要或层级压缩。
- 当 context 接近模型上限时，系统没有 tokenizer 估算，也没有按信息类型分配预算，容易出现 prompt 超长、模型调用失败、关键上下文被模型侧截断。
- 工具调用历史、中间结果、Harness 报错、Reviewer 反馈只在 GraphState/AgentTask 里被保存，缺少可复用的 memory 抽象；普通 Chat 和 Vibe Coding 的记忆体系不统一。
- 系统指令、项目规范、检索代码、对话历史、测试反馈没有差异化管理策略，全部作为自然语言 prompt 混在一起，后续调试和优化成本较高。

**影响程度：** high

**改进方向：**

引入 `ContextManager`，按 `system_policy / project_rules / retrieved_code / conversation_history / tool_results / current_task` 分 bucket 管理上下文，并基于 tokenizer 做预算分配。超过预算时优先保留系统指令、当前需求、最近工具错误和高相关代码，历史对话走滚动摘要，低相关代码片段做函数级摘要压缩。

**改动范围：**

预计涉及 5~8 个文件，约 350~700 行：新增 `app/engine/context/manager.py`、`summarizer.py`、会话持久化 model/schema，并改造 `chat.py`、`planner.py`、`coder.py`、`qa.py` 的 prompt 构建逻辑。

**面试叙事角度：**

可以讲“我把一个容易超上下文的 Agent 改造成有 token budget、分层记忆和摘要压缩能力的工程化系统，解决了长任务稳定性和成本控制问题”。

## 4. Human-in-the-loop 机制

**现状描述：**

- `aI-coding-workspace-backend/app/engine/workflow.py::human_approval_node` 使用 LangGraph `interrupt()`，在 Planner 生成 SDD 方案后暂停，等待用户审批。
- `aI-coding-workspace-backend/app/engine/workflow.py::compile_async_workflow` 使用 `AsyncSqliteSaver` checkpoint，支持基于 `thread_id` 的中断恢复。
- `aI-coding-workspace-backend/app/api/v1/endpoints/vibe.py::start_vibe` 保存 `AgentTask`，状态为 `waiting_approval` 时返回 `interrupt_payload`。
- `aI-coding-workspace-backend/app/api/v1/endpoints/vibe.py::confirm_vibe` 使用 `Command(resume={approved, feedback})` 恢复工作流，人工反馈会进入 `review_feedback`，并被 `coder_agent` 后续读取。
- `aI-coding-workspace-backend/app/api/v1/endpoints/vibe.py::apply_diff` 会直接执行 `git apply --check` 和 `git apply`，属于高风险文件写入动作。

**缺陷 / 缺失：**

- HIL 目前只覆盖“方案审批”，没有覆盖低置信度决策、高风险写文件、外部 API 调用、Git 操作、消息发送等动作。
- Checkpoint 有基础能力，但缺少可视化 checkpoint 列表、恢复点选择、失败后从某个节点重跑等产品化能力。
- 人工反馈可以进入后续 Coder，但反馈结构比较粗，只是字符串，没有结构化为 `change_request / reject_reason / constraints / risk_acceptance`。
- `apply_diff` 虽然做了 `git apply --check`，但缺少二次确认、风险摘要、影响文件预览、禁止越界路径等安全护栏。

**影响程度：** medium

**改进方向：**

增加 `RiskPolicy` 和 `ApprovalGate`：给每类动作定义风险等级，低风险自动执行，中高风险生成审批卡片，用户确认后再继续。把人工反馈结构化写入 GraphState，并在 checkpoint 元数据中记录审批人、审批时间、风险等级和恢复节点。

**改动范围：**

预计涉及 5~9 个文件，约 300~600 行：改造 `workflow.py`、`vibe.py`、`state.py`、前端 `VibeTab.vue`/store，并新增 `app/engine/policy/risk.py`。

**面试叙事角度：**

可以讲“我不是简单让 Agent 自动写代码，而是设计了风险分级和人工审批机制，把 AI 自动化放进可控的软件交付流程里”。

## 5. Agent 评估框架（Evaluation）

**现状描述：**

- 当前没有发现独立的 `eval` 模块、评估数据集、评估 CLI 或 LangSmith/Arize 集成。
- `aI-coding-workspace-backend/app/engine/harness.py::run_harness` 和 `app/engine/agents/tester.py::tester_agent` 能在生成代码后运行测试，但这是运行期质量门禁，不是离线评估框架。
- `aI-coding-workspace-backend/app/engine/agents/reviewer.py::reviewer_agent` 能输出规范、性能、安全审查结果，但没有把评分项量化沉淀为可横向对比的 eval 指标。
- `AgentTask.output_payload` 会保存单次 Vibe 结果，但没有统一记录 trajectory、节点耗时、模型输入输出、工具选择是否正确、参数是否合理等评估事件。

**缺陷 / 缺失：**

- 无法系统回答“Agent 改版后是否更好”，只能看单次结果或人工感受。
- 评估粒度偏最终结果，没有完整追踪 trajectory，例如 Router 是否路由正确、Planner 是否覆盖边界、Coder 是否生成最小 diff、Tester/Reviewer 是否有效拦截问题。
- 工具调用选择、参数质量、失败恢复次数、token 成本、耗时没有量化追踪。
- 如果要做模型替换、prompt 调优、RAG 策略优化，目前缺少可复现的 benchmark。

**影响程度：** high

**改进方向：**

引入最小可用 eval pipeline：定义 `eval_cases/*.yaml` 测试集，记录 expected files、expected behavior、must-pass tests、rubric；执行时复用现有 LangGraph workflow，输出 trajectory JSONL，并用规则评分 + LLM-as-judge 评分生成报告。第一期无需接 LangSmith，可先做本地 `python -m app.eval.run`。

**改动范围：**

预计涉及 8~12 个文件，约 600~1200 行：新增 `app/eval/`、`eval_cases/`、trajectory logger、评分器、报告生成器，并在 workflow 节点前后插入事件记录。

**面试叙事角度：**

可以讲“我把 Agent 从 demo 能跑推进到可评估、可回归、可量化优化的工程系统，能支撑模型和 prompt 的持续迭代”。

## 6. Tool 检索与路由（Tool Retrieval）

**现状描述：**

- `aI-coding-workspace-backend/app/models/agent_config.py::AgentConfig.tools` 和 `app/schemas/agent_config.py::AgentConfigBase.tools` 保存的是字符串列表。
- `aI-coding-workspace-backend/app/api/v1/endpoints/agents.py::init_builtin_agents` 内置配置里主要是 `["rag_search"]`，更像能力标签，不是真正可执行 tool schema。
- `aI-coding-workspace-backend/app/api/v1/endpoints/chat.py::chat_stream` 加载 AgentConfig 时只使用 `system_prompt` 和 `temperature`，没有把 `tools` 注入模型，也没有执行 tool call。
- `aI-coding-workspace-backend/app/engine/agents/router.py::router_agent` 只做任务类型路由，例如 `vibe_coding` 或 `code_qa`，不是工具级路由。
- 当前没有发现 MCP Client、MCP Server、tool registry、tool embedding index 或动态工具选择逻辑。

**缺陷 / 缺失：**

- 当前不是“全量工具注入”，也不是“按需工具检索”，而是尚未形成真正的工具调用层。
- 当工具数超过 20 个时，现有结构无法根据任务动态选择相关工具子集，也无法避免工具描述语义相似导致的选择混乱。
- 工具描述质量无法被验证，因为 `tools` 只是字符串标签，没有 name、description、input_schema、risk_level、executor 等标准字段。
- 暂不支持 MCP，但现有 AgentConfig 与 workflow 节点可以作为接入 MCP 的上层入口，改造空间存在。

**影响程度：** medium

**改进方向：**

建设 `ToolRegistry`：统一注册本地工具和 MCP 工具，字段包括 `name / description / input_schema / risk_level / tags / executor`。当工具数量少时直接注入候选集，超过阈值后基于 embedding 检索 Top-K，再由 Router/Planner 选择工具并记录选择理由。

**改动范围：**

预计涉及 8~15 个文件，约 700~1400 行：新增 `app/engine/tools/registry.py`、`retriever.py`、`mcp_client.py`，改造 AgentConfig、Chat/Vibe workflow、前端 Agent 配置页。

**面试叙事角度：**

可以讲“我设计了从字符串能力标签到标准化 Tool Registry 的演进方案，让 Agent 具备可扩展工具生态和 MCP 接入能力”。

## 7. Streaming 与中间状态可见性

**现状描述：**

- `aI-coding-workspace-backend/app/api/v1/endpoints/chat.py::chat_stream` 已支持 SSE，包含 `status / context / token / done / error` 事件。
- `aI-coding-workspace-frontend/src/api/index.ts::streamChat` 使用 `fetch + ReadableStream` 解析 SSE，前端可以 token-by-token 展示 Chat 输出。
- `aI-coding-workspace-backend/app/api/v1/endpoints/vibe.py::stream_vibe_events` 暴露 `/vibe/{thread_id}/events`，尝试通过 `graph.astream_events(..., version="v2")` 输出 LangGraph 事件。
- `aI-coding-workspace-frontend/src/api/index.ts::subscribeVibeEvents` 与 `src/stores/app.ts::startSse` 会订阅 Vibe 事件，并保留最近 200 条。
- `aI-coding-workspace-backend/app/engine/state.py::GraphState.current_node` 已有当前节点字段，workflow 节点也会写入 `current_node`。

**缺陷 / 缺失：**

- Chat token streaming 已实现，但 Vibe 的事件订阅更像“旁路监听”，`start_vibe` 和 `confirm_vibe` 本身仍是普通 HTTP 请求，长任务执行时前端不一定能稳定拿到同一次 run 的完整事件。
- 中间状态没有统一事件模型，缺少 `run_started / node_started / node_finished / tool_started / tool_finished / approval_required / retry_scheduled / run_finished` 这样的业务事件。
- 工具参数、节点耗时、token 成本、Harness 命令、Reviewer 结果没有稳定对外暴露，只能从最终 result 或原始 LangGraph event 里解析。
- 缺少事件持久化和重放能力，页面刷新后只剩 `AgentTask` 历史，没有完整运行轨迹。

**影响程度：** medium

**改进方向：**

增加 `RunEvent` 事件表和 `EventBus`，workflow 每个节点显式发布结构化事件，同时 SSE 从事件总线读取；前端显示业务事件而不是直接依赖 LangGraph 原始事件。长任务可改成后台 task + run_id，前端订阅 run_id 获取进度。

**改动范围：**

预计涉及 6~10 个文件，约 400~900 行：新增 `models/run_event.py`、`engine/events.py`，改造 `workflow.py`、`vibe.py`、`tester.py`、`reviewer.py`、前端事件面板。

**面试叙事角度：**

可以讲“我把黑盒 Agent 执行过程改造成可观测、可追踪、可回放的事件流，让前端和研发都能实时理解 Agent 在做什么”。

## Top 3 贡献建议

**第 1 名：Context Budget & Memory Manager**

- 一句话描述：为 Chat 和 Vibe 工作流引入统一上下文预算、分层记忆、摘要压缩和历史持久化机制。
- 来源维度：代码分析-维度3
- 入口文件：`aI-coding-workspace-backend/app/api/v1/endpoints/chat.py`、`app/engine/agents/planner.py`、`app/engine/agents/coder.py`
- 为什么适合我：与你简历里的 Tree-Sitter 多语言语义切片、Code RAG、SDD Agent 工作流高度相关，能把“能检索”升级为“会管理上下文”。
- 预计工作量：中
- 面试中能讲什么：能讲 token budget、上下文分层、滚动摘要、工具结果保真、长任务稳定性和成本控制。
- 风险点：需要选择 tokenizer；摘要压缩可能丢关键细节，需要评估集验证。

**第 2 名：Agent Eval & Trajectory Logger**

- 一句话描述：新增本地 eval pipeline，记录完整 trajectory，并用规则评分与 LLM-as-judge 评估 Agent 表现。
- 来源维度：代码分析-维度5
- 入口文件：`aI-coding-workspace-backend/app/engine/workflow.py`、`app/engine/harness.py`、新增 `app/eval/`
- 为什么适合我：你已经有 Harness 测试闭环和 Reviewer 质量门禁，补 Eval 能形成“生成-测试-审查-评估-优化”的完整工程闭环。
- 预计工作量：中到大
- 面试中能讲什么：能体现你不是只会调 prompt，而是能设计可回归、可量化、可持续优化的 Agent 工程体系。
- 风险点：评估样本设计需要代表性；LLM-as-judge 需要控制成本和一致性。

**第 3 名：Risk-aware HIL + 可观测执行事件流**

- 一句话描述：把现有方案审批扩展为风险分级审批，并将 Agent 执行过程沉淀为可订阅、可持久化、可回放的业务事件。
- 来源维度：代码分析-维度4 / 维度7
- 入口文件：`aI-coding-workspace-backend/app/engine/workflow.py`、`app/api/v1/endpoints/vibe.py`、`aI-coding-workspace-frontend/src/stores/app.ts`
- 为什么适合我：与你“内部开发流程落地 AI Coding Agent”的定位匹配，能体现工程安全、流程治理和产品化落地能力。
- 预计工作量：中
- 面试中能讲什么：能讲 LangGraph interrupt/checkpoint、审批恢复、风险策略、SSE 事件广播、Agent 可观测性。
- 风险点：事件模型要设计稳定，否则前后端会被原始 LangGraph 事件绑定；审批太重会影响自动化效率。

