"""架构约束检查 —— ``python scripts/check_architecture.py``。

把「单向依赖、抽象边界、单一技术出口、强制类型注解」写成可执行断言，避免
重构后悄悄退化。检查对象是当前五层包（models / infra / service / viewmodel /
view），全部基于 AST，不 import 业务代码、不需要窗口。

规则：

1. View → ViewModel → Service → Infra，所有层可引用 Models；禁止反向与跨层；
2. ``flet_video`` 只允许出现在 view/native_video.py，应用代码禁止直接 import flet；
3. 所有函数都有返回注解，所有参数（self/cls 除外）都有类型注解。
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "cs_video_player"
LAYERS = ("models", "infra", "service", "viewmodel", "view")

# 每层允许向下依赖的集合（models 只依赖自己）
ALLOWED: dict[str, frozenset[str]] = {
    "models": frozenset({"models"}),
    "infra": frozenset({"models", "infra"}),
    "service": frozenset({"models", "infra", "service"}),
    "viewmodel": frozenset({"models", "service", "viewmodel"}),
    "view": frozenset({"models", "viewmodel", "view"}),
}

problems: list[str] = []


def _layer_of(path: Path) -> str | None:
    try:
        rel = path.relative_to(PACKAGE)
    except ValueError:
        return None
    return rel.parts[0] if rel.parts and rel.parts[0] in LAYERS else None


def _imported_layers(tree: ast.Module) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        module: str | None = None
        if isinstance(node, ast.ImportFrom) and node.module:
            module = node.module
        elif isinstance(node, ast.Import):
            module = next(
                (alias.name for alias in node.names if alias.name.startswith("cs_video_player.")),
                None,
            )
        if module and module.startswith("cs_video_player."):
            parts = module.split(".")
            if len(parts) > 1 and parts[1] in LAYERS:
                found.add(parts[1])
    return found


def _check_annotations(tree: ast.Module, rel: str) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        where = f"{rel}:{node.lineno} {node.name}"
        if node.returns is None:
            problems.append(f"缺少返回注解 -> {where}")
        args = node.args
        for arg in (
            *args.posonlyargs,
            *args.args,
            *args.kwonlyargs,
        ):
            if arg.arg in {"self", "cls"}:
                continue
            if arg.annotation is None:
                problems.append(f"参数 {arg.arg} 缺少注解 -> {where}")
        if args.vararg is not None and args.vararg.annotation is None:
            problems.append(f"参数 *{args.vararg.arg} 缺少注解 -> {where}")
        if args.kwarg is not None and args.kwarg.annotation is None:
            problems.append(f"参数 **{args.kwarg.arg} 缺少注解 -> {where}")


def _check_file(path: Path) -> None:
    rel = path.relative_to(PACKAGE).as_posix()
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    layer = _layer_of(path)

    if layer is not None:
        illegal = _imported_layers(tree) - ALLOWED[layer]
        for target in sorted(illegal):
            problems.append(f"跨层依赖 {layer} -> {target} ({rel})")

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and "flet_video" in node.module:
            if rel != "view/native_video.py":
                problems.append(f"flet_video 只允许出现在 view/native_video.py ({rel})")
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "flet_video" in alias.name and rel != "view/native_video.py":
                    problems.append(f"flet_video 只允许出现在 view/native_video.py ({rel})")
                if alias.name == "flet" or alias.name.startswith("flet."):
                    problems.append(f"应用代码禁止直接 import flet ({rel})")

    _check_annotations(tree, rel)


def main() -> int:
    if not PACKAGE.exists():
        print(f"PACKAGE_MISSING {PACKAGE}")
        return 1
    for path in sorted(PACKAGE.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        _check_file(path)

    if problems:
        print(f"ARCH_FAIL ({len(problems)} 项)")
        for problem in problems:
            print("ARCH_PROBLEM", problem)
        return 1
    print("ARCH_OK 五层单向依赖 / flet_video 单点 / 强制类型注解")
    return 0


if __name__ == "__main__":
    sys.exit(main())
