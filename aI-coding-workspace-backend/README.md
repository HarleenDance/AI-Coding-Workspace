# AI Coding Workspace Backend

Web 版 AI IDE 后端骨架，目标是实现一个 Cursor / Trae 迷你版的代码库智能工作台。当前版本聚焦后端核心链路：项目代码解析、AST 语义切片、pgvector Code RAG、DeepSeek 模型路由、LangGraph 多 Agent 工作流，以及 Vibe Coding 的人工确认中断与恢复。

## 技术栈

- Python `>=3.12`
- FastAPI `0.137.2`
- Pydantic `>=2.7.0`
- LangGraph `1.2.6`
- LangChain `>=1.3.10`
- langchain-openai `>=1.3.2`
- SQLAlchemy `>=2.0.30`
- PostgreSQL `16+`
- pgvector
- asyncpg
- tree-sitter
- pygments
- DeepSeek Chat / DeepSeek Reasoner via LangChain 1.x `ChatOpenAI`
- DashScope text-embedding-v3 / Qwen3-Embedding

## 目录结构

```text
aI-coding-workspace-backend/
├── app/
│   ├── api/v1/endpoints/
│   │   ├── chat.py
│   │   └── vibe.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── dependencies.py
│   ├── models/
│   │   ├── base.py
│   │   └── project.py
│   ├── schemas/
│   │   ├── chat.py
│   │   └── vibe.py
│   ├── engine/
│   │   ├── parser/
│   │   │   └── code_slicer.py
│   │   ├── vector/
│   │   │   ├── embeddings.py
│   │   │   ├── indexer.py
│   │   │   └── retriever.py
│   │   ├── agents/
│   │   │   ├── router.py
│   │   │   ├── planner.py
│   │   │   ├── coder.py
│   │   │   ├── qa.py
│   │   │   └── llm.py
│   │   ├── state.py
│   │   └── workflow.py
│   └── main.py
├── runtime/
├── pyproject.toml
└── README.md
```

## 核心能力

### 1. Code RAG

代码索引链路位于 `app/engine/vector/indexer.py`：

1. 从项目根目录递归读取源码文件。
2. 使用 `tree-sitter` 对 Python、JavaScript、TypeScript、Java、Go 等语言做函数 / 类级语义切片。
3. 对不支持或解析失败的文件自动退化为文件级切片。
4. 调用 DashScope / Qwen Embedding 生成向量。
5. 使用 SQLAlchemy 异步写入 PostgreSQL `code_chunks` 表。
6. 通过 pgvector HNSW 索引执行相似度检索。

### 2. LangGraph Agent 工作流

工作流定义位于 `app/engine/workflow.py`：

```text
START
  ↓
router_agent
  ├── code_qa / project_analysis / defect_scan → qa_agent → END
  └── vibe_coding → planner_agent → human_approval_node
                                      ├── reject → END
                                      └── accept → coder_agent → END
```

Agent 职责：

- `router_agent`：使用 DeepSeek Chat 做用户意图识别。
- `planner_agent`：使用 DeepSeek Reasoner 生成 Vibe Coding 修改方案。
- `human_approval_node`：使用 LangGraph `interrupt()` 暂停，等待用户确认。
- `coder_agent`：使用 DeepSeek Chat 根据已批准方案生成 unified diff。
- `qa_agent`：基于检索上下文回答代码库问题。

### 3. Vibe Coding HIL 闭环

Vibe Coding 的人工确认链路：

1. 前端调用 `POST /api/vibe/start` 提交开发需求。
2. 后端创建 `thread_id`，检索代码上下文并启动 LangGraph。
3. `planner_agent` 生成 Markdown + Mermaid 的修改方案。
4. `human_approval_node` 调用 `interrupt()` 暂停执行。
5. 前端展示方案，用户选择 Accept / Reject。
6. 前端调用 `POST /api/vibe/confirm`。
7. 后端使用 `Command(resume=...)` 恢复 LangGraph。
8. 若通过确认，`coder_agent` 生成具体 diff。

## 配置

配置类位于 `app/core/config.py`，环境变量统一使用 `AI_IDE_` 前缀。

示例 `.env`：

```env
AI_IDE_DATABASE_URL=postgresql+asyncpg://postgres:123456@localhost:5432/ai_workspace_db

AI_IDE_DEEPSEEK_BASE_URL=https://api.deepseek.com
AI_IDE_DEEPSEEK_API_KEY=your_deepseek_api_key
AI_IDE_DEEPSEEK_CHAT_MODEL=deepseek-chat
AI_IDE_DEEPSEEK_REASONER_MODEL=deepseek-reasoner

AI_IDE_DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
AI_IDE_DASHSCOPE_API_KEY=your_dashscope_api_key
AI_IDE_EMBEDDING_MODEL=text-embedding-v3
AI_IDE_EMBEDDING_DIMENSION=1024

AI_IDE_CHECKPOINT_SQLITE_PATH=runtime/langgraph_checkpoints.sqlite3
```

注意：`AI_IDE_EMBEDDING_DIMENSION` 必须与 `CodeChunk.embedding = Vector(1024)` 的数据库字段维度一致。如果切换为其他维度模型，需要同步修改模型和迁移脚本。

## 数据模型

模型定义位于 `app/models/project.py`。

- `Project`：项目元数据。
- `ProjectFile`：项目文件映射和符号索引。
- `CodeChunk`：代码语义切片，包含 pgvector `embedding` 字段。
- `AgentTask`：Agent 执行任务追踪。
- `AgentLog`：节点事件、模型输出、SSE 日志记录。

生产库需要启用 pgvector 扩展。项目已经提供初始化脚本，会自动执行：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

如果执行时报错：

```text
extension "vector" is not available
```

说明 PostgreSQL 服务端尚未安装 pgvector 扩展文件。Windows 下官方推荐方式是安装 Visual Studio C++ Build Tools 后编译 pgvector：

```cmd
set "PGROOT=D:\tools\PostgreSQL\18"
cd %TEMP%
git clone --branch v0.8.3 https://github.com/pgvector/pgvector.git
cd pgvector
nmake /F Makefile.win
nmake /F Makefile.win install
```

安装完成后重启 PostgreSQL，再执行：

```powershell
$env:PGPASSWORD="123456"
psql -h localhost -p 5432 -U postgres -d ai_workspace_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

如果数据库 `ai_workspace_db` 已经存在，可以直接运行纯 SQL 初始化：

```powershell
$env:PGPASSWORD="123456"
psql -h localhost -p 5432 -U postgres -d ai_workspace_db -f scripts/init_schema.sql
```

也可以在 Python 依赖安装完成后运行 SQLAlchemy 初始化脚本：

```powershell
python scripts/init_db.py
```

该脚本会完成：

- 检查数据库连接。
- 创建 pgvector 扩展。
- 根据 SQLAlchemy 模型创建表。
- 创建 `projects`、`project_files`、`code_chunks`、`agent_tasks`、`agent_logs` 等核心表。

检查连接：

```powershell
python scripts/check_db.py
```

## API

默认 API 前缀是 `/api`。

### 代码库问答

```http
POST /api/chat
Content-Type: application/json

{
  "project_id": "00000000-0000-0000-0000-000000000000",
  "question": "这个项目的认证流程是怎样的？"
}
```

响应：

```json
{
  "answer": "...",
  "artifacts": {
    "answer": "..."
  }
}
```

### 启动 Vibe Coding

```http
POST /api/vibe/start
Content-Type: application/json

{
  "project_id": "00000000-0000-0000-0000-000000000000",
  "requirement": "给项目增加基于 JWT 的登录接口"
}
```

典型响应：

```json
{
  "thread_id": "generated-thread-id",
  "status": "waiting_approval",
  "interrupt_payload": {
    "type": "vibe_plan_approval",
    "thread_id": "generated-thread-id",
    "project_id": "00000000-0000-0000-0000-000000000000",
    "proposed_plan": "..."
  }
}
```

### 确认 Vibe Coding 方案

```http
POST /api/vibe/confirm
Content-Type: application/json

{
  "thread_id": "generated-thread-id",
  "approved": true,
  "feedback": "方案通过，但请优先保持现有目录结构。"
}
```

响应会包含最终 LangGraph 执行结果，`generated_artifacts.diff` 中保存生成的 unified diff。

### SSE 事件流

```http
GET /api/vibe/{thread_id}/events
```

返回 `text/event-stream`，用于前端实时展示 LangGraph 节点切换、模型流式输出和结构化 Agent 状态。

## 本地运行

安装依赖后，在项目根目录运行：

```powershell
uvicorn app.main:app --reload
```

访问：

```text
http://127.0.0.1:8000/docs
```

数据库健康检查：

```text
GET http://127.0.0.1:8000/api/health/db
```

## 当前实现边界

当前代码是企业级核心骨架，已经实现核心模块边界和关键链路，但仍建议在正式生产前补齐：

- Alembic 数据库迁移。
- 项目 zip 上传、解压、路径安全校验和后台索引任务。
- `AgentTask` / `AgentLog` 与 SSE 的持久化日志打通。
- DeepSeek Reasoner token 流到 SSE 的完整转发。
- Redis / PostgreSQL 级别的分布式 checkpointer。
- 代码 diff 应用、沙箱执行、测试运行和回滚机制。
- API 鉴权、租户隔离、速率限制和审计日志。

## 开发约定

- Python 代码使用 3.12+ 原生类型标注。
- 数据库访问统一使用 SQLAlchemy 2.x async API。
- Agent 节点之间只通过 `GraphState` 共享状态，避免隐藏耦合。
- 模型路由集中在 `DeepSeekClient`，使用 LangChain 1.x 标准异步模型接口，后续可替换为多供应商路由器。
- 业务状态持久化和 LangGraph checkpointer 分离，便于扩展到多实例部署。
