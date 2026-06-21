# AI Coding Workspace 项目导读

> 一句话：**对标 Cursor / Trae 的 Web 版 AI 代码 IDE**，用户上传 ZIP 项目即可获得代码问答（RAG）、Vibe Coding（多智能体 + Human-in-the-Loop）、多模型切换、智能体配置等能力，全程浏览器内完成。

---

## 1. 这是什么项目

一个**全栈 AI 编程助手**，核心能力：

| 能力 | 说明 |
|---|---|
| 项目托管 | 上传 ZIP → 解压入库 → 文件树浏览 → 在线编辑（Monaco）→ Ctrl+S 保存 |
| 代码问答 | 向量检索（pgvector）+ LLM 流式回答（SSE）+ 多轮上下文 |
| Vibe Coding | 自然语言需求 → Planner 规划 → **人工审批** → Coder 生成 diff → 一键 Apply |
| 多模型 | DeepSeek / 通义千问 / Kimi / GLM / OpenAI 任选，运行时可切换 |
| 智能体 | 代码助手 / 架构师 / 审查员 / 文档生成器，支持自定义 + @ 切换 |
| IDE 体验 | VSCode 式布局：活动栏、菜单栏、命令面板、多 Tab、右键追加代码到对话框 |

---

## 2. 技术栈一览

```
┌─────────────────────────────────────────────────────┐
│  Frontend (Vue 3 + TS + Vite)                       │
│  ├─ Element Plus / Monaco Editor / markdown-it       │
│  ├─ Pinia 状态管理 / vue-i18n 国际化（中/英）        │
│  └─ SSE 流式 / Vite chunk 拆分                       │
├─────────────────────────────────────────────────────┤
│  Backend (FastAPI + LangGraph + SQLAlchemy)         │
│  ├─ LangGraph 状态机：Router → Planner → HIL → Coder │
│  ├─ tree-sitter AST 切片 + pgvector 向量检索        │
│  ├─ MultiModelClient：OpenAI 兼容协议统一接入        │
│  └─ SSE / Interrupt-Resume（HIL 审批闭环）           │
├─────────────────────────────────────────────────────┤
│  Data (PostgreSQL 18 + pgvector)                    │
│  ├─ projects / project_files / code_chunks          │
│  ├─ agent_configs / model_configs                   │
│  └─ code_chunks.embedding (vector(1024))             │
├─────────────────────────────────────────────────────┤
│  AI Providers                                        │
│  ├─ DeepSeek (chat / reasoner)                       │
│  └─ DashScope (text-embedding-v3, 1024 维)          │
└─────────────────────────────────────────────────────┘
```

---

## 3. 30 秒看懂核心流程

### 3.1 代码问答（RAG）
```
用户提问 → embed(question) → pgvector cosine_distance topK → 拼上下文 → LLM 流式回答
```

### 3.2 Vibe Coding（HIL 闭环）
```
需求 → Router 分类 → Planner 生成方案 → [interrupt 暂停]
                                              ↓
                            前端展示方案 ← 用户审批
                                              ↓
                              approved? → Coder 生成 diff → Apply
```

---

## 4. 项目目录结构

```
AI Coding Workspace/
├── aI-coding-workspace-backend/        # FastAPI 后端
│   └── app/
│       ├── api/v1/endpoints/           # 路由：projects/chat/vibe/agents/models
│       ├── engine/
│       │   ├── agents/                 # LangGraph 节点：router/planner/coder/qa
│       │   ├── parser/code_slicer.py   # tree-sitter AST 切片
│       │   ├── vector/                 # embedding + retriever + indexer
│       │   ├── state.py                # GraphState TypedDict
│       │   └── workflow.py             # 图构建 + compile + HIL
│       ├── models/                     # SQLAlchemy: Project/File/Chunk/Agent/Model
│       ├── schemas/                    # Pydantic
│       └── core/                       # config / database / dependencies
├── aI-coding-workspace-frontend/       # Vue 3 前端
│   └── src/
│       ├── components/                 # ActivityBar/MenuBar/ChatTab/CodePanel...
│       ├── stores/app.ts               # Pinia 全局状态
│       ├── api/                        # axios + SSE
│       └── i18n/                       # zh.ts / en.ts
├── deploy/                             # nginx.conf / postgresql.conf / deploy.sh
├── docker-compose.yml                  # 生产编排
├── start.bat / stop.bat                # Windows 一键启停
└── PROJECT_DOC.md                      # 完整项目文档
```

---

## 5. 快速启动

```bash
# 1. 启动数据库
docker run --name pgvector-db -e POSTGRES_PASSWORD=123456 -p 5433:5432 -d pgvector/pgvector:pg18

# 2. 配置后端 .env（aI-coding-workspace-backend/.env）
AI_IDE_DATABASE_URL=postgresql+asyncpg://postgres:123456@localhost:5433/ai_workspace_db
AI_IDE_DEEPSEEK_API_KEY=sk-xxx
AI_IDE_DASHSCOPE_API_KEY=sk-xxx

# 3. 初始化数据库 + 启动后端
cd aI-coding-workspace-backend
python scripts/init_db.py
uvicorn app.main:app --reload --port 8000

# 4. 启动前端
cd aI-coding-workspace-frontend
npm install && npm run dev

# 5. 访问
open http://localhost:5173
```

---

## 6. 亮点（面试可讲）

1. **LangGraph + Interrupt-Resume 实现 Human-in-the-Loop**：Planner 暂停等用户审批，用 SQLite checkpointer 持久化图状态
2. **tree-sitter AST 语义切片**：不是粗暴按行切，而是按函数/类切，检索精度高
3. **pgvector 向量检索**：cosine_distance + HNSW 索引，毫秒级 topK
4. **MultiModelClient 统一抽象**：所有国产模型（OpenAI 兼容协议）一个接口接入
5. **SSE 流式 + 状态机事件流**：前端实时看到「检索中 → 思考中 → token 流」
6. **Monaco 右键追加代码到对话**：选中代码 → 右键 → 带 context 发问
7. **生产部署优化**：swap + 内存限制 + chunk 拆分，4G 阿里云可跑

---

## 7. 详细文档

完整的架构设计、难点剖析、优化过程、面试题、简历写法见 **[PROJECT_DOC.md](./PROJECT_DOC.md)**。
