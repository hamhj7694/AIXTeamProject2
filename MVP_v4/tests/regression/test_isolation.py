from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from scripts.verify_self_contained import ROOT, audit, inventory
from scripts.verify_env_example import audit as env_audit


@pytest.fixture
def isolated_root():
    (ROOT / ".cache").mkdir(exist_ok=True)
    with TemporaryDirectory(dir=ROOT / ".cache") as directory:
        root = Path(directory)
        (root / "frontend/src").mkdir(parents=True)
        (root / "backend").mkdir()
        yield root


@pytest.mark.parametrize("content,rule", [
    ('import MVP_v3', 'legacy_runtime_reference'),
    ('import sys\nsys.path.insert(0, "outside")', 'path_injection'),
    ('path = "../../other_project/file.py"', 'relative_path_escapes_root'),
    ('path = "C:/Users/example/model.pkl"', 'external_absolute_path'),
])
def test_forbidden_runtime_patterns_fail(isolated_root, content, rule):
    (isolated_root / "backend/module.py").write_text(content, encoding="utf-8")
    result = audit(isolated_root)
    assert not result["passed"]
    assert rule in [issue["rule"] for issue in result["violations"]]


def test_direct_uuid_is_rejected_outside_helper(isolated_root):
    (isolated_root / "frontend/src/Component.tsx").write_text("crypto.randomUUID()", encoding="utf-8")
    assert any(v["rule"] == "direct_uuid_outside_helper" for v in audit(isolated_root)["violations"])


def test_missing_env_name_is_reported_without_values(isolated_root):
    (isolated_root / ".env.example").write_text("APP_ENV=test\n", encoding="utf-8")
    (isolated_root / "backend/module.py").write_text('import os\nos.getenv("REQUIRED_NAME")', encoding="utf-8")
    result = env_audit(isolated_root)
    assert result["missing_names"] == ["REQUIRED_NAME"]
    assert result["real_env_files_read"] == 0


def test_application_passes_current_audits():
    assert audit()["passed"], audit()["violations"]
    assert env_audit()["passed"], env_audit()["missing_names"]


def test_dependency_directory_is_not_traversed(isolated_root):
    (isolated_root / "node_modules").mkdir()
    (isolated_root / "node_modules/ignored.py").write_text('import MVP_v3', encoding="utf-8")
    assert inventory(isolated_root)[0] == []
