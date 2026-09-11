from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


MANIFEST_VERSION = "1.0.0"
@dataclass
class ScanAudit:
    """읽은 파일을 기록해 Scanner가 허용 범위를 벗어나지 않았는지 검증한다."""

    root: Path
    read_paths: set[str] = field(default_factory=set)

    def record(self, path: Path) -> str:
        relative = repository_relative(self.root, path)
        if path.name.startswith(".env"):
            raise PermissionError(f"Scanner denied environment file access: {relative}")
        self.read_paths.add(relative)
        return relative


def repository_relative(root: Path, path: Path) -> str:
    root = root.resolve()
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"Path is outside MVP_v3: {resolved.name}") from exc
    if re.match(r"^[A-Za-z]:", relative) or relative.startswith("/"):
        raise ValueError("Only repository-relative paths are allowed")
    return relative


def read_text(path: Path, audit: ScanAudit) -> str:
    audit.record(path)
    return path.read_text(encoding="utf-8")


def read_json(path: Path, audit: ScanAudit) -> Any:
    return json.loads(read_text(path, audit))


def sha256_file(path: Path, audit: ScanAudit) -> str:
    audit.record(path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evidence(source_path: str, reason: str, line: int | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"source_path": source_path, "reason": reason}
    if line is not None:
        item["line"] = line
    return item


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def manifest_hash(manifests: dict[str, Any]) -> str:
    """실행 시각 같은 volatile field가 없는 AUTO manifest만 hash한다."""

    payload = {name: manifests[name] for name in sorted(manifests)}
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git_snapshot(root: Path) -> tuple[str, bool | None]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True,
            capture_output=True, text=True, encoding="utf-8",
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--short", "--untracked-files=all"], cwd=root, check=True,
            capture_output=True, text=True, encoding="utf-8",
        ).stdout.strip()
        return commit, bool(status)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "unknown", None


def validate_manifest(value: dict[str, Any], schema: dict[str, Any]) -> None:
    """현재 schema가 요구하는 top-level contract를 표준 라이브러리로 검사한다."""

    for key in schema.get("required", []):
        if key not in value:
            raise ValueError(f"Manifest missing required field: {key}")
    manifest_type = value.get("manifest_type")
    allowed = schema.get("properties", {}).get("manifest_type", {}).get("enum", [])
    if manifest_type not in allowed:
        raise ValueError(f"Unknown manifest_type: {manifest_type}")
    for rule in schema.get("allOf", []):
        expected = rule.get("if", {}).get("properties", {}).get("manifest_type", {}).get("const")
        if manifest_type != expected:
            continue
        for key in rule.get("then", {}).get("required", []):
            if key not in value:
                raise ValueError(f"{manifest_type} manifest missing required field: {key}")


def source_line(text: str, needle: str) -> int | None:
    for number, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return number
    return None
