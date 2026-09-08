from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .common import ScanAudit, evidence, read_text, repository_relative, sha256_file, source_line


def scan_ai_ml(root: Path, audit: ScanAudit, endpoints: list[dict[str, Any]]) -> dict[str, Any]:
    ai_main_path = root / "backend/ai_api/app/main.py"
    general_main_path = root / "backend/general_api/app/main.py"
    model_adapter_path = root / "backend/ai_api/app/domains/diagnosis/model_adapter.py"
    retrieval_path = root / "backend/general_api/app/domains/cases/case_retrieval.py"
    workflow_path = root / "backend/ai_api/app/domains/case_support/workflow.py"
    snapshot_path = root / "backend/ai_api/app/domains/case_support/case_snapshot_adapter.py"
    copilot_path = root / "backend/ai_api/app/domains/case_support/copilot_service.py"
    work_card_path = root / "backend/ai_api/app/domains/case_support/work_card_service.py"
    final_report_path = root / "backend/ai_api/app/domains/case_support/final_report_service.py"

    texts = {
        path: read_text(path, audit)
        for path in (
            ai_main_path, general_main_path, model_adapter_path, retrieval_path,
            workflow_path, snapshot_path, copilot_path, work_card_path, final_report_path,
        )
    }
    endpoint_map = {(item["component_id"], item["path"]): item for item in endpoints}

    snapshot_kind = (
        "RULE_BASED_PROJECTION"
        if "AsyncOpenAI" not in texts[snapshot_path] and "사용하지 않는다" in texts[workflow_path]
        else "UNVERIFIED"
    )
    definitions = [
        ("text-analysis", "Text Analysis", "ai-api", "/ai/analyze/text", "LLM_ML_HYBRID", ai_main_path),
        ("window-analysis", "Window Analysis", "ai-api", "/ai/analyze/windows", "LLM_ML_HYBRID", ai_main_path),
        ("feature-extraction", "Feature Extraction", "ai-api", "/ai/features/extract", "STRUCTURED_FEATURE", ai_main_path),
        ("risk-prediction", "Risk Prediction", "ai-api", "/ai/risk/predict", "ML", model_adapter_path),
        ("case-support-snapshot", "Case Support Snapshot", "ai-api", "/ai/case-support/snapshot", snapshot_kind, snapshot_path),
        ("case-copilot", "Case Copilot", "ai-api", "/ai/case-copilot/replies", "LLM", copilot_path),
        ("work-card", "Work Card", "ai-api", "/ai/work-cards/generate", "LLM", work_card_path),
        ("final-report", "Final Report", "ai-api", "/ai/final-reports/generate", "LLM", final_report_path),
        ("customer-support", "Customer Support", "general-api", "/api/cases/{case_id}/ai/customer-replies", "LLM_ORCHESTRATION", copilot_path),
    ]
    services = []
    for identifier, name, component, endpoint_path, kind, implementation_path in definitions:
        endpoint = endpoint_map.get((component, endpoint_path))
        if endpoint is None:
            continue
        endpoint_evidence = evidence(endpoint["source_path"], f"{endpoint['method']} {endpoint_path}", endpoint["line"])
        implementation_source = repository_relative(root, implementation_path)
        service_evidence = [endpoint_evidence]
        if implementation_source != endpoint["source_path"]:
            service_evidence.append(evidence(implementation_source, f"{kind} implementation"))
        services.append({
            "id": identifier,
            "name": name,
            "component_id": component,
            "endpoint": endpoint_path,
            "method": endpoint["method"],
            "implementation_kind": kind,
            "status": "CURRENT",
            "human_review": identifier not in {"window-analysis", "feature-extraction", "risk-prediction"},
            "evidence": service_evidence,
            "source_paths": sorted({item["source_path"] for item in service_evidence}),
        })

    adapter_text = texts[model_adapter_path]
    filename_match = re.search(r'MODEL_FILENAME\s*=\s*["\']([^"\']+)', adapter_text)
    expected_match = re.search(r'EXPECTED_SHA256\s*=\s*["\']([a-fA-F0-9]{64})', adapter_text)
    version_match = re.search(r'sklearn\.__version__\s*!=\s*["\']([^"\']+)', adapter_text)
    artifact_path = root / "backend/ai_api/models" / (filename_match.group(1) if filename_match else "")
    actual_hash = sha256_file(artifact_path, audit) if filename_match and artifact_path.is_file() else None
    expected_hash = expected_match.group(1).lower() if expected_match else None
    artifact = {
        "name": filename_match.group(1) if filename_match else None,
        "source_path": repository_relative(root, artifact_path) if filename_match and artifact_path.exists() else None,
        "sha256": actual_hash,
        "expected_sha256": expected_hash,
        "hash_matches_code": bool(actual_hash and expected_hash and actual_hash == expected_hash),
        "required_sklearn_version": version_match.group(1) if version_match else None,
        "status": "EXPERIMENTAL" if filename_match and "EXPERIMENTAL" in filename_match.group(1) else "UNVERIFIED",
        "inspection": "FILE_METADATA_AND_SHA256_ONLY",
        "evidence": [evidence(repository_relative(root, model_adapter_path), "Artifact filename, expected hash and runtime guard")],
    }
    if artifact["source_path"]:
        artifact["evidence"].append(evidence(artifact["source_path"], "Artifact file exists and SHA-256 was calculated without deserialization"))

    retrieval_text = texts[retrieval_path]
    retrieval = {
        "id": "case-lexical-retrieval",
        "name": "Case-scoped lexical retrieval",
        "component_id": "general-api",
        "status": "CURRENT" if "class CaseRetriever" in retrieval_text else "UNVERIFIED",
        "implementation_kind": "TF_IDF_CHARACTER_NGRAM",
        "consumer": "ai-api",
        "source_paths": [repository_relative(root, retrieval_path)],
        "evidence": [evidence(repository_relative(root, retrieval_path), "Authorized Case-local character n-gram retrieval", source_line(retrieval_text, "class CaseRetriever"))],
    }

    unimplemented_domains = []
    for name in ("knowledge", "voice"):
        directory = root / "backend/ai_api/app/domains" / name
        python_files = sorted(path for path in directory.glob("*.py") if path.is_file())
        if not python_files:
            unimplemented_domains.append({"name": name, "status": "UNVERIFIED", "reason": "No Python implementation files"})

    return {
        "services": sorted(services, key=lambda item: item["id"]),
        "retrieval": retrieval,
        "ml_artifact": artifact,
        "unimplemented_domains": unimplemented_domains,
        "safety_facts": {
            "case_support_snapshot": snapshot_kind,
            "lexical_retrieval_owner": "general-api",
            "raw_input_storage_detected": "input_text" in read_text(root / "database/01_mysql_csr_schema.sql", audit),
            "inactive_case_brief_llm_path": "LLM 보강 경로" in texts[workflow_path] and "사용하지 않는다" in texts[workflow_path],
        },
    }
