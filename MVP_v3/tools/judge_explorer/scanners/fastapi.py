from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from .common import ScanAudit, read_text, repository_relative


HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _expression(value: ast.AST | None) -> str | int | None:
    if value is None:
        return None
    if isinstance(value, ast.Constant) and isinstance(value.value, (str, int)):
        return value.value
    try:
        return ast.unparse(value)
    except Exception:
        return None


def scan_fastapi_file(root: Path, path: Path, component_id: str, audit: ScanAudit) -> dict[str, Any]:
    text = read_text(path, audit)
    tree = ast.parse(text, filename=path.name)
    source = repository_relative(root, path)
    endpoints = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            if not isinstance(decorator.func.value, ast.Name) or decorator.func.value.id != "app":
                continue
            method = decorator.func.attr.lower()
            if method not in HTTP_METHODS or not decorator.args:
                continue
            path_value = _expression(decorator.args[0])
            if not isinstance(path_value, str):
                continue
            keywords = {item.arg: item.value for item in decorator.keywords if item.arg}
            endpoints.append({
                "component_id": component_id,
                "method": method.upper(),
                "path": path_value,
                "handler": node.name,
                "response_model": _expression(keywords.get("response_model")),
                "status_code": _expression(keywords.get("status_code")),
                "source_path": source,
                "line": decorator.lineno,
            })
    return {
        "component_id": component_id,
        "source_path": source,
        "endpoints": sorted(endpoints, key=lambda item: (item["path"], item["method"], item["handler"])),
    }


def scan_fastapi(root: Path, audit: ScanAudit) -> dict[str, Any]:
    general = scan_fastapi_file(root, root / "backend/general_api/app/main.py", "general-api", audit)
    ai = scan_fastapi_file(root, root / "backend/ai_api/app/main.py", "ai-api", audit)
    return {"services": [general, ai], "endpoints": [*general["endpoints"], *ai["endpoints"]]}

