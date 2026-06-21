CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    owner_id UUID,
    original_zip_name VARCHAR(512) NOT NULL,
    root_path VARCHAR(1024) NOT NULL,
    description TEXT,
    is_indexed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS project_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    path VARCHAR(1024) NOT NULL,
    language VARCHAR(64) NOT NULL,
    size_bytes BIGINT NOT NULL DEFAULT 0,
    content_hash VARCHAR(128) NOT NULL,
    symbol_index JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS code_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    file_id UUID NOT NULL REFERENCES project_files(id) ON DELETE CASCADE,
    file_path VARCHAR(1024) NOT NULL,
    language VARCHAR(64) NOT NULL,
    symbol_name VARCHAR(512),
    symbol_type VARCHAR(64) NOT NULL DEFAULT 'module',
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding vector(1024) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id VARCHAR(128) NOT NULL,
    project_id UUID,
    task_type VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'running',
    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES agent_tasks(id) ON DELETE CASCADE,
    thread_id VARCHAR(128) NOT NULL,
    node_name VARCHAR(128),
    level VARCHAR(16) NOT NULL DEFAULT 'info',
    event_type VARCHAR(64),
    message TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_project_files_project_id
    ON project_files(project_id);

CREATE INDEX IF NOT EXISTS ix_project_files_content_hash
    ON project_files(content_hash);

CREATE INDEX IF NOT EXISTS ix_code_chunks_project_id
    ON code_chunks(project_id);

CREATE INDEX IF NOT EXISTS ix_code_chunks_file_id
    ON code_chunks(file_id);

CREATE INDEX IF NOT EXISTS ix_code_chunks_embedding_hnsw
    ON code_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS ix_agent_tasks_thread_id
    ON agent_tasks(thread_id);

CREATE INDEX IF NOT EXISTS ix_agent_tasks_project_id
    ON agent_tasks(project_id);

CREATE INDEX IF NOT EXISTS ix_agent_tasks_task_type
    ON agent_tasks(task_type);

CREATE INDEX IF NOT EXISTS ix_agent_logs_thread_id
    ON agent_logs(thread_id);

CREATE INDEX IF NOT EXISTS ix_agent_logs_node_name
    ON agent_logs(node_name);

CREATE INDEX IF NOT EXISTS ix_agent_logs_event_type
    ON agent_logs(event_type);

