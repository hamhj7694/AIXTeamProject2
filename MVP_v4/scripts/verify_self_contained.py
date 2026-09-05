"""Static application isolation audit. Never opens real environment files or follows links."""
import ast
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".cache", ".pytest_cache", "dist", "test-results", "playwright-report"}
SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".json", ".toml", ".ini", ".yaml", ".yml", ".sh", ".service", ".conf", ".html", ".css", ".sql"}


def is_secret_name(name: str) -> bool:
    return name != ".env.example" and (name == ".env" or name.startswith(".env."))


def is_link(path: Path) -> bool:
    if path.is_symlink():
        return True
    # Python 3.11 Windows junctions also carry the reparse-point flag.
    return bool(getattr(path.lstat(), "st_file_attributes", 0) & 0x400)


def inventory(root: Path):
    files, links = [], []
    for directory, names, filenames in os.walk(root, followlinks=False):
        base = Path(directory)
        kept = []
        for name in names:
            path = base / name
            if is_link(path):
                links.append(path)
            elif name not in SKIP_DIRS:
                kept.append(name)
        names[:] = kept
        for name in filenames:
            path = base / name
            if is_secret_name(name):
                continue  # Do not open, hash, copy or search secrets.
            if is_link(path):
                links.append(path)
            else:
                files.append(path)
    return files, links


def audit(root: Path = ROOT) -> dict:
    root = root.resolve()
    files, links = inventory(root)
    violations = [{"file": str(p.relative_to(root)), "rule": "symlink_or_junction"} for p in links]
    scanned = 0
    for path in files:
        relative = path.relative_to(root).as_posix()
        # Documentation/provenance and test fixtures may describe forbidden patterns.
        if relative.split('/')[0] not in {"backend", "frontend", "deploy"}:
            continue
        if "/tests/" in relative or path.suffix not in SOURCE_SUFFIXES:
            continue
        content = path.read_text(encoding="utf-8-sig")
        scanned += 1
        def flag(rule):
            violations.append({"file": relative, "rule": rule})
        patterns = {
            "legacy_runtime_reference": r"MVP_v3|frontend-v3|backend-v3",
            "path_injection": r"sys\s*\.\s*path|PYTHONPATH",
            "external_absolute_path": r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]|/mnt/data(?:/|\b)|/Users/|/tmp/|/var/tmp/",
        }
        for rule, pattern in patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                flag(rule)
        if relative.startswith("frontend/src/"):
            if re.search(r"https?://(?:localhost|127\.0\.0\.1|\d{1,3}(?:\.\d{1,3}){3})", content):
                flag("browser_hardcoded_api")
            if path != root / "frontend/src/shared/uuid.ts" and "randomUUID" in content:
                flag("direct_uuid_outside_helper")
        # Relative import/file literals must resolve inside the application root.
        literals = re.findall(r'''["'](\.\.?[\\/][^"'\n]+)["']''', content)
        for literal in literals:
            target = (path.parent / literal.replace("\\", "/")).resolve()
            if not target.is_relative_to(root):
                flag("relative_path_escapes_root")
        if path.name in {"package.json", "package-lock.json"}:
            if re.search(r'"(?:file:|link:|workspace:)', content):
                flag("local_package_dependency")
        if path.suffix == ".py":
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.level:
                        target = path.parent
                        for _ in range(node.level - 1):
                            target = target.parent
                        if not target.is_relative_to(root):
                            flag("python_relative_import_escapes_root")
            except SyntaxError:
                flag("python_syntax_invalid")
    return {"passed": not violations, "scanned_application_files": scanned,
            "symlinks_or_junctions": len(links), "violations": violations,
            "scope": "application source/config/deploy; docs/tests/dependency installations/runtime cache excluded from text patterns"}


if __name__ == "__main__":
    result = audit()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
