"""Git 集成接口：对项目目录执行 git 操作。"""
import asyncio
import functools
import re
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.dependencies import DbSession
from app.models.project import Project

router = APIRouter(prefix="/projects/{project_id}/git", tags=["Git"])


class GitError(HTTPException):
    pass


def _run_git_sync(project_root: Path, args: tuple[str, ...]) -> tuple[int, str, str]:
    """同步执行 git 命令，返回 (returncode, stdout, stderr)。"""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            shell=False,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        raise RuntimeError("未找到 git 命令，请检查环境")
    except subprocess.TimeoutExpired:
        raise RuntimeError("git 命令执行超时")


async def _run_git(project_root: Path, *args: str) -> str:
    """异步执行 git 命令，返回 stdout。失败抛 HTTPException。"""
    if not project_root.is_dir():
        raise HTTPException(status_code=404, detail=f"项目目录不存在: {project_root}")

    loop = asyncio.get_event_loop()
    try:
        returncode, out, err = await loop.run_in_executor(
            None, functools.partial(_run_git_sync, project_root, args)
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if returncode != 0:
        raise HTTPException(
            status_code=400,
            detail=f"git {' '.join(args)} 失败: {err or out}",
        )
    return out


async def _get_project_root(session: DbSession, project_id: str) -> Path:
    try:
        project = await session.get(Project, project_id)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"无效的项目 ID: {project_id} ({e})",
        )
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    root = Path(project.root_path)
    if not root.is_absolute():
        # 相对路径基于项目运行目录解析
        from app.core.config import get_settings
        root = get_settings().runtime_dir.parent / root
    return root


def _parse_porcelain_status(text: str) -> list[dict]:
    """解析 git status --porcelain=v1 -z 的输出。"""
    files = []
    for line in text.splitlines():
        if not line:
            continue
        # 格式：XY <path> 或 XY <path> -> <new path>
        xy = line[:2]
        path_part = line[3:]
        status_map = {
            "M": "modified",
            "A": "added",
            "D": "deleted",
            "R": "renamed",
            "C": "copied",
            "U": "unmerged",
            "?": "untracked",
        }
        staged = status_map.get(xy[0], "modified")
        working = status_map.get(xy[1], "" if xy[1] == " " else "modified")
        files.append({
            "path": path_part,
            "staged_status": staged,
            "working_status": working,
            "is_staged": xy[0] not in (" ", "?"),
            "is_untracked": xy == "??",
        })
    return files


@router.get("/status")
async def git_status(project_id: str, session: DbSession) -> dict:
    """获取 git 状态（变更文件列表 + 分支 + ahead/behind）。"""
    root = await _get_project_root(session, project_id)

    # 确保是 git 仓库（.git 可能是目录或文件-submodule）
    git_marker = root / ".git"
    if not git_marker.exists():
        return {
            "initialized": False,
            "branch": "",
            "ahead_behind": {"ahead": 0, "behind": 0},
            "files": [],
        }

    # 用 rev-parse 验证确实是 git 仓库（避免 .git 损坏）
    try:
        await _run_git(root, "rev-parse", "--is-inside-work-tree")
    except HTTPException:
        return {
            "initialized": False,
            "branch": "",
            "ahead_behind": {"ahead": 0, "behind": 0},
            "files": [],
        }

    try:
        status_out = await _run_git(root, "status", "--porcelain=v1", "-b")
    except HTTPException as e:
        # git status 失败，返回带错误的可用状态
        return {
            "initialized": True,
            "branch": "",
            "ahead_behind": {"ahead": 0, "behind": 0},
            "files": [],
            "error": e.detail,
        }

    lines = status_out.splitlines()
    branch_line = lines[0] if lines else ""
    files_text = "\n".join(lines[1:])

    # 解析分支行：## main 或 ## main...origin/main [ahead 2]
    branch = ""
    ahead = behind = 0
    if branch_line.startswith("## "):
        rest = branch_line[3:]
        # 去掉 ahead/behind 标记
        bracket_idx = rest.find("[")
        branch_part = rest[:bracket_idx] if bracket_idx >= 0 else rest
        track_part = rest[bracket_idx:] if bracket_idx >= 0 else ""

        # 分支名（取第一个 token，去掉 ...origin/main）
        branch = branch_part.split("...")[0].strip()

        # 解析 ahead/behind
        for m in re.finditer(r"(ahead|behind)\s+(\d+)", track_part):
            if m.group(1) == "ahead":
                ahead = int(m.group(2))
            else:
                behind = int(m.group(2))
    elif branch_line.startswith("No commits yet") or "Initial commit" in branch_line:
        branch = "main"

    return {
        "initialized": True,
        "branch": branch,
        "ahead_behind": {"ahead": ahead, "behind": behind},
        "files": _parse_porcelain_status(files_text),
    }


@router.get("/diff")
async def git_diff(
    project_id: str,
    session: DbSession,
    staged: bool = False,
    path: str | None = None,
) -> dict:
    """获取 diff（整体或单个文件）。"""
    root = await _get_project_root(session, project_id)
    args = ["diff"]
    if staged:
        args.append("--cached")
    if path:
        args += ["--", path]
    diff_text = await _run_git(root, *args)
    return {"diff": diff_text}


class GitStageRequest(BaseModel):
    paths: list[str] = Field(default_factory=list, description="要暂存的文件，空则全部暂存")


@router.post("/stage")
async def git_stage(
    project_id: str,
    payload: GitStageRequest,
    session: DbSession,
) -> dict:
    root = await _get_project_root(session, project_id)
    if payload.paths:
        await _run_git(root, "add", "--", *payload.paths)
    else:
        await _run_git(root, "add", "-A")
    return {"message": "已暂存"}


class GitUnstageRequest(BaseModel):
    paths: list[str] = Field(default_factory=list)


@router.post("/unstage")
async def git_unstage(
    project_id: str,
    payload: GitUnstageRequest,
    session: DbSession,
) -> dict:
    root = await _get_project_root(session, project_id)
    if payload.paths:
        await _run_git(root, "reset", "HEAD", "--", *payload.paths)
    else:
        await _run_git(root, "reset", "HEAD")
    return {"message": "已取消暂存"}


class GitCommitRequest(BaseModel):
    message: str
    description: str | None = None


@router.post("/commit")
async def git_commit(
    project_id: str,
    payload: GitCommitRequest,
    session: DbSession,
) -> dict:
    root = await _get_project_root(session, project_id)
    full_msg = payload.message
    if payload.description:
        full_msg = f"{payload.message}\n\n{payload.description}"
    out = await _run_git(root, "commit", "-m", full_msg)
    # 提取 commit hash
    commit_hash = ""
    m = re.match(r"\[(?:[\w\-/]+)\s+([a-f0-9]+)\]", out)
    if m:
        commit_hash = m.group(1)
    return {"message": "已提交", "commit": commit_hash, "output": out}


@router.get("/log")
async def git_log(
    project_id: str,
    session: DbSession,
    limit: int = 30,
) -> dict:
    """获取提交历史。"""
    root = await _get_project_root(session, project_id)
    log_fmt = "%H|%h|%an|%ae|%at|%s"
    out = await _run_git(root, "log", f"--pretty=format:{log_fmt}", f"-{limit}")
    commits = []
    for line in out.splitlines():
        parts = line.split("|", 5)
        if len(parts) == 6:
            commits.append({
                "hash": parts[0],
                "short_hash": parts[1],
                "author": parts[2],
                "email": parts[3],
                "timestamp": int(parts[4]) if parts[4].isdigit() else 0,
                "subject": parts[5],
            })
    return {"commits": commits}


@router.get("/branches")
async def git_branches(project_id: str, session: DbSession) -> dict:
    root = await _get_project_root(session, project_id)
    out = await _run_git(root, "branch", "--list", "-v")
    current = ""
    branches = []
    for line in out.splitlines():
        line = line.rstrip()
        if not line:
            continue
        is_current = line.startswith("*")
        if is_current:
            current = line[1:].strip().split()[0]
        parts = (line.lstrip("* ").split())
        if parts:
            branches.append(parts[0])
    return {"current": current, "branches": branches}


class GitCheckoutRequest(BaseModel):
    branch: str


@router.post("/checkout")
async def git_checkout(
    project_id: str,
    payload: GitCheckoutRequest,
    session: DbSession,
) -> dict:
    root = await _get_project_root(session, project_id)
    await _run_git(root, "checkout", payload.branch)
    return {"message": f"已切换到 {payload.branch}"}


@router.post("/init")
async def git_init(project_id: str, session: DbSession) -> dict:
    """对项目目录初始化 git 仓库。"""
    root = await _get_project_root(session, project_id)
    if (root / ".git").exists():
        return {"message": "已是 git 仓库"}
    await _run_git(root, "init")
    await _run_git(root, "add", "-A")
    await _run_git(root, "commit", "-m", "Initial commit")
    return {"message": "已初始化并提交"}
