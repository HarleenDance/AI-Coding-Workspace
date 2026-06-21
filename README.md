# AI Coding Workspace

Web 版 AI 代码 IDE，对标 Cursor / Trae。

## 快速启动

### 首次启动（需要初始化数据库）

```powershell
# 1. 启动数据库容器（首次）
docker run --name pgvector-db -e POSTGRES_PASSWORD=123456 -p 5433:5432 -d pgvector/pgvector:pg18

# 2. 初始化表结构
cd aI-coding-workspace-backend
& "D:\Roaming\pyenv-win\pyenv-win\versions\3.12.0\python.exe" scripts/init_db.py

# 3. 配置 .env（在后端目录下）
#    AI_IDE_DATABASE_URL=postgresql+asyncpg://postgres:123456@localhost:5433/ai_workspace_db
#    AI_IDE_DEEPSEEK_API_KEY=你的key
#    AI_IDE_DASHSCOPE_API_KEY=你的key
```

### 日常启动

```powershell
# 一键启动前后端
powershell -ExecutionPolicy Bypass -File start.ps1

# 停止所有服务
powershell -ExecutionPolicy Bypass -File stop.ps1
```

启动后：
- 前端: http://localhost:5173
- 后端 API 文档: http://localhost:8000/docs
- 局域网（手机）: http://<你的IP>:5173

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + TypeScript + Element Plus + Monaco Editor |
| 后端 | FastAPI + LangGraph + SQLAlchemy |
| 数据库 | PostgreSQL 18 + pgvector |
| AI | DeepSeek (Chat/Reasoner) + DashScope (Embedding) |

## 功能

- 上传 ZIP 项目 → 文件树浏览
- Code Chat（流式 SSE + 多轮上下文 + RAG 检索）
- Vibe Coding（需求 → 方案审批 → diff 生成 → 一键 Apply）
- 代码编辑 + Ctrl+S 保存
- 双模代码搜索（关键词 + 语义向量）
- Agent 执行历史
- 响应式适配（手机端 Tab 布局）
