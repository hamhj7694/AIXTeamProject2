"""Copy V4, install from a local wheelhouse into a new venv, deny original-repo reads."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import sys

from scripts.verify_self_contained import ROOT, inventory, audit


def main() -> None:
    wheels = ROOT / ".cache/model-wheelhouse"
    if not wheels.is_dir() or not any(wheels.glob("*.whl")):
        raise SystemExit("Prepare requirements wheels in .cache/model-wheelhouse first")
    files, links = inventory(ROOT)
    if links:
        raise SystemExit("Refusing to copy linked application files")
    parent = Path(tempfile.mkdtemp(prefix="model-isolation-", dir=ROOT / ".cache"))
    copied = parent / "MVP_v4"
    copied.mkdir()
    for source in files:
        relative = source.relative_to(ROOT)
        destination = copied / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    wheel_copy = copied / ".cache/wheels"
    wheel_copy.mkdir(parents=True)
    for wheel in wheels.glob("*.whl"):
        shutil.copyfile(wheel, wheel_copy / wheel.name)
    report = {"task": "P0-006", "passed": False, "scope": "copied V4 + fresh Python 3.11 venv + real ML inference only",
              "copy_directory": str(copied.relative_to(ROOT)), "not_run": ["frontend build in copy", "copy DB migration", "product E2E"]}
    try:
        assert sys.version_info[:2] == (3, 11)
        subprocess.run([sys.executable, "-m", "venv", str(copied / ".venv")], check=True)
        python = copied / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        subprocess.run([str(python), "-E", "-s", "-m", "pip", "install", "--no-index", "--no-cache-dir",
                        "--find-links", str(wheel_copy), "--disable-pip-version-check", "--quiet",
                        "-r", "backend/requirements.txt"], cwd=copied, check=True)
        subprocess.run([str(python), "-m", "pip", "check"], cwd=copied, check=True)
        probe = subprocess.run([str(python), "-E", "-s", "-m", "backend.scripts.isolated_model_probe",
                                "--forbidden-root", str(ROOT.parent)], cwd=copied, capture_output=True,
                               encoding="utf-8", check=True)
        report["probe"] = json.loads(probe.stdout)
        report["static_audit"] = audit(copied)
        report["passed"] = report["probe"]["passed"] and report["static_audit"]["passed"]
        if not report["passed"]:
            raise RuntimeError("Copied model isolation failed")
    except subprocess.CalledProcessError as error:
        report["failure"] = {"exit_code": error.returncode, "stderr": error.stderr or "See command output"}
        raise
    finally:
        (ROOT / "docs/evidence/model_isolation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
