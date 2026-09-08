from __future__ import annotations

import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path


TOOL_ROOT = Path(__file__).resolve().parents[1]
MVP_ROOT = TOOL_ROOT.parents[1]
sys.path.insert(0, str(TOOL_ROOT))

from generate_metadata import generate_all  # noqa: E402
from scanners.common import ScanAudit, canonical_json  # noqa: E402


class JudgeMetadataGeneratorTest(unittest.TestCase):
    def generate(self, suffix: str):
        base = Path(tempfile.gettempdir()) / f"judge-explorer-test-{suffix}"
        return generate_all(MVP_ROOT, base, generated_at=f"2026-01-01T00:00:0{suffix[-1]}+00:00")

    def test_deterministic_auto_content_and_manifest_hash(self) -> None:
        first, _ = self.generate("run-1")
        second, _ = self.generate("run-2")
        for name in first:
            if name == "build_snapshot.json":
                continue
            self.assertEqual(canonical_json(first[name]), canonical_json(second[name]))
        self.assertEqual(first["build_snapshot.json"]["manifest_hash"], second["build_snapshot.json"]["manifest_hash"])
        self.assertNotEqual(first["build_snapshot.json"]["metadata_generated_at"], second["build_snapshot.json"]["metadata_generated_at"])

    def test_scanner_read_audit_denies_environment_and_absolute_paths(self) -> None:
        manifests, audit = self.generate("audit-3")
        self.assertTrue(audit.read_paths)
        self.assertFalse(any(Path(path).name.startswith(".env") for path in audit.read_paths))
        serialized = canonical_json(manifests)
        self.assertNotIn(str(MVP_ROOT).replace("\\", "/"), serialized.replace("\\", "/"))
        self.assertNotRegex(serialized, r"[A-Za-z]:[/\\]Users[/\\]")

    def test_secret_denylist_rejects_every_dot_env_filename(self) -> None:
        audit = ScanAudit(MVP_ROOT)
        for name in (".env", ".env.example", ".env.production"):
            with self.assertRaises(PermissionError):
                audit.record(MVP_ROOT / name)

    def test_current_items_have_code_evidence(self) -> None:
        manifests, _ = self.generate("evidence-4")
        for component in manifests["architecture.json"]["components"]:
            if component["status"] == "CURRENT":
                self.assertTrue(component["evidence"], component["id"])
        for service in manifests["ai_manifest.json"]["services"]:
            if service["status"] == "CURRENT":
                self.assertTrue(service["evidence"], service["id"])

    def test_schema_contract_and_known_manifest_types(self) -> None:
        manifests, _ = self.generate("schema-5")
        expected = {"architecture", "technologies", "api", "ai", "deployment", "database", "build_snapshot"}
        self.assertEqual({item["manifest_type"] for item in manifests.values()}, expected)
        for value in manifests.values():
            self.assertEqual(value["manifest_version"], "1.0.0")

    def test_artifact_is_hashed_without_deserialization_imports(self) -> None:
        manifests, _ = self.generate("artifact-6")
        artifact = manifests["ai_manifest.json"]["ml_artifact"]
        self.assertEqual(artifact["inspection"], "FILE_METADATA_AND_SHA256_ONLY")
        self.assertTrue(artifact["hash_matches_code"])
        source = (TOOL_ROOT / "scanners/ai_ml.py").read_text(encoding="utf-8")
        imports = {
            node.names[0].name
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Import) and node.names
        }
        self.assertFalse({"pickle", "joblib"} & imports)

    def test_fastapi_scanner_does_not_import_application(self) -> None:
        source = (TOOL_ROOT / "scanners/fastapi.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(item.name for item in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        self.assertFalse(any(name.startswith(("fastapi", "general_api", "ai_api")) for name in imported))

    def test_code_backed_safety_facts(self) -> None:
        manifests, _ = self.generate("facts-7")
        facts = manifests["ai_manifest.json"]["safety_facts"]
        self.assertEqual(facts["lexical_retrieval_owner"], "general-api")
        self.assertEqual(facts["case_support_snapshot"], "RULE_BASED_PROJECTION")
        self.assertTrue(facts["raw_input_storage_detected"])
        self.assertTrue(facts["inactive_case_brief_llm_path"])


if __name__ == "__main__":
    unittest.main()
