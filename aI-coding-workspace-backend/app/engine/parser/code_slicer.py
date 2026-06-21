from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from pygments.lexers import get_lexer_for_filename
from pygments.util import ClassNotFound


@dataclass(frozen=True, slots=True)
class CodeSlice:
    file_path: str
    language: str
    symbol_name: str | None
    symbol_type: str
    start_line: int
    end_line: int
    content: str
    metadata: dict


LANGUAGE_SYMBOL_NODES = {
    "python": {"function_definition", "class_definition"},
    "javascript": {"function_declaration", "class_declaration", "method_definition"},
    "typescript": {"function_declaration", "class_declaration", "method_definition"},
    "tsx": {"function_declaration", "class_declaration", "method_definition"},
    "java": {"method_declaration", "class_declaration", "interface_declaration"},
    "go": {"function_declaration", "method_declaration", "type_declaration"},
}

LANGUAGE_ALIASES = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "tsx": "tsx",
    "java": "java",
    "go": "go",
}


def detect_language(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    if suffix in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[suffix]

    try:
        lexer = get_lexer_for_filename(path.name)
    except ClassNotFound:
        return "text"

    aliases = lexer.aliases or []
    return aliases[0] if aliases else "text"


def _extract_symbol_name(source: bytes, node) -> str | None:
    """从 tree-sitter 节点中抽取符号名。

    不同语言 grammar 对名字节点的命名不完全一致，因此采用保守匹配。
    """
    for child in node.children:
        if child.type in {"identifier", "type_identifier", "property_identifier"}:
            return source[child.start_byte:child.end_byte].decode(
                "utf-8",
                errors="ignore",
            )
    return None


def _get_tree_sitter_parser(language: str):
    """加载 tree-sitter parser。

    tree-sitter 的各语言 grammar 发布方式较分散，企业项目建议固定使用
    tree-sitter-language-pack 并在启动时预热。若未安装对应 grammar，本函数返回
    None，调用方会退化到文件级切片，保证索引任务不中断。
    """
    try:
        from tree_sitter_language_pack import get_parser

        return get_parser(language)
    except Exception:
        return None


def _build_file_level_slice(
    *,
    relative_path: str,
    language: str,
    source_text: str,
    fallback_reason: str,
) -> CodeSlice:
    return CodeSlice(
        file_path=relative_path,
        language=language,
        symbol_name=None,
        symbol_type="module",
        start_line=1,
        end_line=max(1, source_text.count("\n") + 1),
        content=source_text,
        metadata={"fallback": fallback_reason},
    )


def slice_code_file(file_path: Path, project_root: Path) -> list[CodeSlice]:
    source_text = file_path.read_text(encoding="utf-8", errors="ignore")
    source_bytes = source_text.encode("utf-8")
    language = detect_language(file_path)
    relative_path = str(file_path.relative_to(project_root)).replace("\\", "/")

    parser = _get_tree_sitter_parser(language)
    if parser is None or language not in LANGUAGE_SYMBOL_NODES:
        return [
            _build_file_level_slice(
                relative_path=relative_path,
                language=language,
                source_text=source_text,
                fallback_reason="unsupported_language_or_missing_grammar",
            ),
        ]

    tree = parser.parse(source_bytes)
    target_nodes = LANGUAGE_SYMBOL_NODES[language]
    slices: list[CodeSlice] = []

    def walk(node) -> None:
        if node.type in target_nodes:
            symbol_name = _extract_symbol_name(source_bytes, node)
            content = source_bytes[node.start_byte:node.end_byte].decode(
                "utf-8",
                errors="ignore",
            )
            slices.append(
                CodeSlice(
                    file_path=relative_path,
                    language=language,
                    symbol_name=symbol_name,
                    symbol_type=node.type,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    content=content,
                    metadata={
                        "start_byte": node.start_byte,
                        "end_byte": node.end_byte,
                    },
                ),
            )
            return

        for child in node.children:
            walk(child)

    walk(tree.root_node)

    if not slices:
        return [
            _build_file_level_slice(
                relative_path=relative_path,
                language=language,
                source_text=source_text,
                fallback_reason="no_symbol_found",
            ),
        ]

    return slices


async def slice_project_files(
    project_id: UUID,
    project_root: Path,
    max_file_size: int = 512 * 1024,
) -> list[CodeSlice]:
    del project_id

    ignored_dirs = {
        ".git",
        ".idea",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
    }
    result: list[CodeSlice] = []

    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in ignored_dirs for part in path.parts):
            continue
        if path.stat().st_size > max_file_size:
            continue

        result.extend(slice_code_file(path, project_root))

    return result

