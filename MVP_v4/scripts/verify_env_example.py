"""Compare code variable names to the one explicitly permitted example file."""
import ast
import json
from pathlib import Path
import re

from scripts.verify_self_contained import ROOT, inventory


def audit(root: Path = ROOT) -> dict:
    example = root / ".env.example"
    declared = set(re.findall(r"^([A-Z][A-Z0-9_]*)=", example.read_text(encoding="utf-8-sig"), re.MULTILINE))
    used = set()
    for path in inventory(root)[0]:
        relative = path.relative_to(root).as_posix()
        if not relative.startswith(("backend/", "frontend/", "deploy/")) or "/tests/" in relative:
            continue
        if path.suffix == ".py":
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if ast.unparse(node.func) in {"os.getenv", "os.environ.get"} and node.args:
                        if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                            used.add(node.args[0].value)
                if isinstance(node, ast.Subscript) and ast.unparse(node.value) == "os.environ":
                    if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                        used.add(node.slice.value)
        elif path.suffix in {".ts", ".tsx", ".js", ".mjs"}:
            used.update(re.findall(r"(?:process|import\.meta)\.env\.([A-Z][A-Z0-9_]*)", path.read_text(encoding="utf-8-sig")))
    missing = sorted(used - declared)
    return {"passed": not missing, "used_names": sorted(used), "missing_names": missing,
            "reserved_names": sorted(declared - used), "real_env_files_read": 0}


if __name__ == "__main__":
    result = audit()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
