import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_TIMEOUT_SECONDS = 180


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_simple_yaml(path: Path) -> dict[str, Any] | None:
    """Read a tiny YAML subset without adding a runtime dependency."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return None

    data: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-") and current_key:
            data.setdefault(current_key, []).append(line[1:].strip().strip("'\""))
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value:
                data[key] = value.strip("'\"")
                current_key = None
            else:
                data[key] = []
                current_key = key
    return data


def discover_harness_commands(project_root: Path) -> list[str]:
    """Discover unit/integration test commands for the project."""
    for name in ("harness.json", ".harness.json"):
        config = _read_json(project_root / name)
        if config:
            commands = config.get("commands") or config.get("tests")
            if isinstance(commands, list):
                return [str(item) for item in commands if str(item).strip()]
            if isinstance(commands, str):
                return [commands]

    for name in ("harness.yml", "harness.yaml", ".harness.yml", ".harness.yaml"):
        config = _read_simple_yaml(project_root / name)
        if config:
            commands = config.get("commands") or config.get("tests")
            if isinstance(commands, list):
                return [str(item) for item in commands if str(item).strip()]
            if isinstance(commands, str):
                return [commands]

    if (project_root / "pyproject.toml").exists() or (project_root / "pytest.ini").exists():
        return ["python -m pytest"]
    if (project_root / "package.json").exists():
        package = _read_json(project_root / "package.json") or {}
        scripts = package.get("scripts") if isinstance(package, dict) else {}
        if isinstance(scripts, dict):
            if "test" in scripts:
                return ["npm test -- --runInBand"]
            if "build" in scripts:
                return ["npm run build"]
    if (project_root / "pom.xml").exists():
        return ["mvn test"]
    if (project_root / "build.gradle").exists() or (project_root / "build.gradle.kts").exists():
        return ["gradle test"]
    return []


async def _run_command(command: str, cwd: Path, timeout_seconds: int) -> dict[str, Any]:
    process = await asyncio.create_subprocess_shell(
        command,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout_seconds,
        )
    except TimeoutError:
        process.kill()
        stdout, stderr = await process.communicate()
        return {
            "command": command,
            "passed": False,
            "return_code": -1,
            "stdout": stdout.decode("utf-8", errors="ignore")[-8000:],
            "stderr": (stderr.decode("utf-8", errors="ignore") + "\nTimed out")[-8000:],
        }

    return {
        "command": command,
        "passed": process.returncode == 0,
        "return_code": process.returncode,
        "stdout": stdout.decode("utf-8", errors="ignore")[-8000:],
        "stderr": stderr.decode("utf-8", errors="ignore")[-8000:],
    }


async def _apply_diff(project_root: Path, diff_text: str) -> dict[str, Any]:
    if not diff_text.strip():
        return {"attempted": False, "passed": True, "message": "No diff generated."}

    with tempfile.NamedTemporaryFile("w", suffix=".diff", delete=False, encoding="utf-8") as fh:
        fh.write(diff_text)
        diff_path = Path(fh.name)

    try:
        check = await _run_command(f'git apply --check "{diff_path}"', project_root, 30)
        if not check["passed"]:
            return {
                "attempted": True,
                "passed": False,
                "message": "Diff failed git apply --check.",
                "stdout": check["stdout"],
                "stderr": check["stderr"],
            }
        apply = await _run_command(f'git apply "{diff_path}"', project_root, 30)
        return {
            "attempted": True,
            "passed": apply["passed"],
            "message": "Diff applied to temporary workspace." if apply["passed"] else "Diff apply failed.",
            "stdout": apply["stdout"],
            "stderr": apply["stderr"],
        }
    finally:
        diff_path.unlink(missing_ok=True)


async def run_harness(
    *,
    project_root: str,
    diff_text: str = "",
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Apply generated code to a temp copy and execute Harness tests."""
    source_root = Path(project_root).resolve()
    if not source_root.is_dir():
        return {
            "passed": False,
            "commands": [],
            "runs": [],
            "error": f"Project root does not exist: {source_root}",
        }

    with tempfile.TemporaryDirectory(prefix="ai-harness-") as temp_dir:
        temp_root = Path(temp_dir) / source_root.name
        ignore = shutil.ignore_patterns(
            ".git",
            ".venv",
            "__pycache__",
            "node_modules",
            "dist",
            "build",
            ".pytest_cache",
        )
        shutil.copytree(source_root, temp_root, ignore=ignore)

        apply_result = await _apply_diff(temp_root, diff_text)
        commands = discover_harness_commands(temp_root)
        if not commands:
            return {
                "passed": apply_result.get("passed", False),
                "commands": [],
                "runs": [],
                "diff_apply": apply_result,
                "summary": "No Harness test command found; only diff validation was performed.",
            }
        if not apply_result.get("passed", False):
            return {
                "passed": False,
                "commands": commands,
                "runs": [],
                "diff_apply": apply_result,
                "summary": "Generated diff could not be applied, so tests were skipped.",
            }

        runs = []
        for command in commands:
            result = await _run_command(command, temp_root, timeout_seconds)
            runs.append(result)
            if not result["passed"]:
                break

        passed = all(item["passed"] for item in runs)
        return {
            "passed": passed,
            "commands": commands,
            "runs": runs,
            "diff_apply": apply_result,
            "summary": "Harness tests passed." if passed else "Harness tests failed.",
        }
