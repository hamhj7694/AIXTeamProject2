"""Phase 0 foundation + local ML gates. Stops at the first failed command."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

from scripts.verify_self_contained import ROOT, audit
from scripts.verify_env_example import audit as env_audit


def main() -> None:
    npm = shutil.which("npm.cmd" if sys.platform == "win32" else "npm")
    if not npm:
        raise SystemExit("npm is required")
    steps = [
        ("actual_model_preflight", [sys.executable, "-m", "backend.scripts.model_preflight", "--record"], ROOT),
        ("backend_contract_regression", [sys.executable, "-m", "pytest", "tests", "-q"], ROOT),
        ("python_dependency_check", [sys.executable, "-m", "pip", "check"], ROOT),
        ("frontend_clean_install", [npm, "ci", "--cache", "../.cache/npm", "--no-audit"], ROOT / "frontend"),
        ("frontend_typecheck", [npm, "run", "typecheck"], ROOT / "frontend"),
        ("frontend_contract_uuid", [npm, "test"], ROOT / "frontend"),
        ("frontend_build", [npm, "run", "build"], ROOT / "frontend"),
    ]
    report = {"task": "P0-006", "scope": "Phase 0 foundation + actual structured-feature ML", "steps": [], "passed": False,
              "not_run": ["Conversational/LLM inference", "final standalone clean install", "Ubuntu nginx/systemd", "product E2E A/B"]}
    destination = ROOT / "docs/evidence/phase0_gate.json"
    try:
        for name, command, cwd in steps:
            print(f"Running {name}", flush=True)
            result = subprocess.run(command, cwd=cwd, check=False)
            report["steps"].append({"gate": name, "exit_code": result.returncode})
            if result.returncode:
                raise SystemExit(result.returncode)
        report["isolation"] = audit()
        report["environment"] = env_audit()
        report["dist"] = (ROOT / "frontend/dist/index.html").is_file() and (ROOT / "frontend/dist/assets").is_dir()
        report["passed"] = report["isolation"]["passed"] and report["environment"]["passed"] and report["dist"]
        if not report["passed"]:
            raise SystemExit(1)
    finally:
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Phase 0 foundation and local ML gates passed. Conversational/product/standalone completion is not claimed.")


if __name__ == "__main__":
    main()
