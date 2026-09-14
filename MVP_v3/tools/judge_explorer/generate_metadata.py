from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scanners.ai_ml import scan_ai_ml
from scanners.common import (
    MANIFEST_VERSION,
    ScanAudit,
    evidence,
    git_snapshot,
    manifest_hash,
    read_json,
    read_text,
    repository_relative,
    validate_manifest,
    write_json,
)
from scanners.database import scan_database
from scanners.deployment import scan_deployment
from scanners.fastapi import scan_fastapi
from scanners.frontend import scan_frontend


AUTO_FILES = {
    "architecture.json": "architecture",
    "technologies.json": "technologies",
    "api_manifest.json": "api",
    "ai_manifest.json": "ai",
    "deployment.json": "deployment",
    "db_manifest.json": "database",
}


def _backend_technologies(root: Path, audit: ScanAudit, deployment: dict[str, Any]) -> list[dict[str, Any]]:
    requirements_path = root / "backend/requirements.txt"
    requirements = read_text(requirements_path, audit)
    source = repository_relative(root, requirements_path)
    technologies = []
    for raw_line in requirements.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"([A-Za-z0-9_.-]+)(.*)", line)
        if not match:
            continue
        technologies.append({
            "name": match.group(1),
            "declared_version": match.group(2) or None,
            "resolved_version": None,
            "scope": "backend",
            "source_paths": [source],
        })
    for dockerfile in deployment["dockerfiles"]:
        for image in dockerfile["images"]:
            name, _, version = image.partition(":")
            technologies.append({
                "name": name,
                "declared_version": version or None,
                "resolved_version": version or None,
                "scope": "container-runtime",
                "source_paths": [dockerfile["source_path"]],
            })
    mysql = next((item for item in deployment["services"] if item["id"] == "mysql"), None)
    if mysql and mysql.get("image"):
        name, _, version = mysql["image"].partition(":")
        technologies.append({
            "name": name,
            "declared_version": version or None,
            "resolved_version": version or None,
            "scope": "database-runtime",
            "source_paths": ["docker-compose.yml"],
        })
    if deployment.get("services"):
        technologies.append({
            "name": "docker",
            "declared_version": None,
            "resolved_version": None,
            "scope": "container-orchestration",
            "source_paths": ["docker-compose.yml"],
        })
    return sorted(technologies, key=lambda item: (item["scope"], item["name"].casefold()))


def _component(
    identifier: str,
    friendly_name: str,
    layer: str,
    technologies: list[str],
    runtime: str,
    status: str,
    responsibilities: list[str],
    dependencies: list[str],
    sources: list[str],
    component_evidence: list[dict[str, Any]],
    port: int | None = None,
) -> dict[str, Any]:
    if status == "CURRENT" and not component_evidence:
        raise ValueError(f"CURRENT component requires evidence: {identifier}")
    return {
        "id": identifier,
        "friendly_name": friendly_name,
        "layer": layer,
        "technologies": technologies,
        "runtime": runtime,
        "port": port,
        "status": status,
        "responsibilities": responsibilities,
        "dependencies": dependencies,
        "source_paths": sorted(set(sources)),
        "evidence": component_evidence,
    }


def _architecture(
    frontend: dict[str, Any], api: dict[str, Any], ai: dict[str, Any],
    deployment: dict[str, Any], database: dict[str, Any],
) -> dict[str, Any]:
    frontend_versions = {item["name"]: item["resolved_version"] or item["declared_version"] for item in frontend["technologies"]}
    dockerfile_by_source = {item["source_path"]: item for item in deployment["dockerfiles"]}
    general_docker = dockerfile_by_source.get("backend/Dockerfile.general-api", {})
    ai_docker = dockerfile_by_source.get("backend/Dockerfile.ai-api", {})
    frontend_docker = dockerfile_by_source.get("frontend/Dockerfile", {})
    general_port = next(iter(general_docker.get("exposed_ports", [])), None)
    ai_port = next(iter(ai_docker.get("exposed_ports", [])), None)
    python_image = next((image for image in general_docker.get("images", []) if image.startswith("python:")), "python:unverified")
    nginx_image = next((image for image in frontend_docker.get("images", []) if image.startswith("nginx:")), "nginx:unverified")
    mysql_service = next((item for item in deployment["services"] if item["id"] == "mysql"), {})
    mysql_image = mysql_service.get("image") or "mysql:unverified"
    general_source = next(item["source_path"] for item in api["services"] if item["component_id"] == "general-api")
    ai_source = next(item["source_path"] for item in api["services"] if item["component_id"] == "ai-api")
    artifact = ai["ml_artifact"]
    components = [
        _component(
            "frontend", "사용자 화면", "presentation",
            [f"React {frontend_versions.get('react', 'unverified')}", f"TypeScript {frontend_versions.get('typescript', 'unverified')}", f"React Router {frontend_versions.get('react-router-dom', 'unverified')}"],
            "Browser", "CURRENT", ["은행·고객 화면", "Shared Case 상호작용"],
            ["nginx", "general-api"], ["frontend/src/App.tsx", "frontend/package.json"],
            [evidence("frontend/src/App.tsx", "BrowserRouter routes and user workspaces"), evidence("frontend/package-lock.json", "Resolved frontend versions")],
        ),
        _component(
            "nginx", "웹 서비스 입구", "web-entry", [nginx_image], nginx_image, "CURRENT",
            ["정적 파일 제공", "SPA fallback", "/api reverse proxy"], ["frontend", "general-api"],
            [deployment["nginx"]["source_path"], "frontend/Dockerfile"], deployment["evidence"][1:2],
            deployment["nginx"]["listen_port"],
        ),
        _component(
            "general-api", "서비스 제어", "service", ["FastAPI", "Uvicorn", "Pydantic", "HTTPX"],
            python_image, "CURRENT", ["공개 REST API", "Case 상태·DB transaction", "AI 호출 조정"],
            ["ai-api", "mysql", "lexical-retrieval"], [general_source, "backend/general_api/app/domains/cases/mysql_repository.py"],
            [evidence(general_source, "General API FastAPI routes"), evidence("backend/general_api/app/domains/cases/mysql_repository.py", "MySQL persistence and transactions")], general_port,
        ),
        _component(
            "lexical-retrieval", "사건 근거 검색", "service-module", ["TF-IDF character n-gram", "Python"],
            "General API process", ai["retrieval"]["status"], ["같은 Case에서 허용된 근거 선별", "고객·은행 공개 범위 분리"],
            ["general-api", "ai-api"], ai["retrieval"]["source_paths"], ai["retrieval"]["evidence"],
        ),
        _component(
            "ai-api", "AI 지원", "ai-service", ["FastAPI", "OpenAI SDK", "scikit-learn"],
            next((image for image in ai_docker.get("images", []) if image.startswith("python:")), "python:unverified"), "CURRENT", ["통화 분석", "Case Copilot", "업무 카드·보고서 생성"],
            ["ml-engine"], [ai_source, "backend/ai_api/app/domains/"],
            [evidence(ai_source, "AI API routes backed by domain services")], ai_port,
        ),
        _component(
            "ml-engine", "위험 확률 계산", "ml", ["scikit-learn", "joblib", "Logistic model"],
            f"scikit-learn {artifact.get('required_sklearn_version') or 'unverified'}", artifact["status"],
            ["Window feature vector 추론", "predict_proba 위험 확률"], ["ai-api"],
            [path for path in [artifact.get("source_path"), "backend/ai_api/app/domains/diagnosis/model_adapter.py"] if path], artifact["evidence"],
        ),
        _component(
            "mysql", "Shared Case Data", "data", [mysql_image], mysql_image, "CURRENT",
            ["Shared Case 영속 상태", "메시지·질문·검증·업무·보고 저장"], ["general-api"],
            [database["base_schema"], "backend/migrations/"], database["evidence"], 3306 if mysql_image != "mysql:unverified" else None,
        ),
        _component(
            "docker-runtime", "서비스 실행환경", "runtime", ["Docker Compose", "Docker"], "Containers", "CURRENT",
            ["Frontend·General API·AI API·MySQL 실행", "내부 네트워크·volume 구성"],
            ["nginx", "general-api", "ai-api", "mysql"], ["docker-compose.yml"], deployment["evidence"][0:1],
        ),
    ]
    edges = [
        {"source": "frontend", "target": "nginx", "type": "HTTP", "direction": "request", "label": "same-origin /api"},
        {"source": "nginx", "target": "general-api", "type": "HTTP_PROXY", "direction": "forward", "label": f"/api → :{general_port}" if general_port else "/api → General API"},
        {"source": "general-api", "target": "lexical-retrieval", "type": "IN_PROCESS", "direction": "query", "label": "authorized Case records"},
        {"source": "lexical-retrieval", "target": "ai-api", "type": "CONTEXT", "direction": "input", "label": "selected retrieved_context"},
        {"source": "general-api", "target": "ai-api", "type": "HTTP", "direction": "request", "label": f"internal AI API :{ai_port}" if ai_port else "internal AI API"},
        {"source": "ai-api", "target": "ml-engine", "type": "IN_PROCESS", "direction": "inference", "label": "feature vector → predict_proba"},
        {"source": "general-api", "target": "mysql", "type": "SQL", "direction": "read_write", "label": "transactional persistence"},
    ]
    return {
        "manifest_version": MANIFEST_VERSION,
        "manifest_type": "architecture",
        "components": sorted(components, key=lambda item: item["id"]),
        "edges": sorted(edges, key=lambda item: (item["source"], item["target"], item["type"])),
    }


def generate_all(
    root: Path,
    output_dir: Path,
    *,
    generated_at: str | None = None,
) -> tuple[dict[str, dict[str, Any]], ScanAudit]:
    root = root.resolve()
    allowed_output = (root / "frontend/public/judge/data/auto").resolve()
    output_dir = output_dir.resolve()
    if output_dir != allowed_output and "judge-explorer-test" not in output_dir.as_posix():
        # Tests use a clearly named temporary directory; production output is fail-closed.
        raise ValueError("Metadata output must be frontend/public/judge/data/auto")

    audit = ScanAudit(root)
    frontend = scan_frontend(root, audit)
    api = scan_fastapi(root, audit)
    deployment = scan_deployment(root, audit)
    database = scan_database(root, audit)
    ai = scan_ai_ml(root, audit, api["endpoints"])
    technologies = {
        "manifest_version": MANIFEST_VERSION,
        "manifest_type": "technologies",
        "technologies": sorted(
            [*frontend["technologies"], *_backend_technologies(root, audit, deployment)],
            key=lambda item: (item["scope"], item["name"].casefold()),
        ),
        "frontend_runtime": frontend,
    }
    api_manifest = {
        "manifest_version": MANIFEST_VERSION,
        "manifest_type": "api",
        "services": api["services"],
        "endpoints": sorted(api["endpoints"], key=lambda item: (item["component_id"], item["path"], item["method"])),
    }
    ai_manifest = {"manifest_version": MANIFEST_VERSION, "manifest_type": "ai", **ai}
    deployment_manifest = {"manifest_version": MANIFEST_VERSION, "manifest_type": "deployment", **deployment}
    database_manifest = {"manifest_version": MANIFEST_VERSION, "manifest_type": "database", **database}
    manifests = {
        "architecture.json": _architecture(frontend, api, ai, deployment, database),
        "technologies.json": technologies,
        "api_manifest.json": api_manifest,
        "ai_manifest.json": ai_manifest,
        "deployment.json": deployment_manifest,
        "db_manifest.json": database_manifest,
    }

    schema_path = root / "tools/judge_explorer/schemas/manifest.schema.json"
    schema = read_json(schema_path, audit)
    for name, value in manifests.items():
        if value["manifest_type"] != AUTO_FILES[name]:
            raise ValueError(f"Unexpected manifest type for {name}")
        validate_manifest(value, schema)

    commit, dirty = git_snapshot(root)
    snapshot = {
        "manifest_version": MANIFEST_VERSION,
        "manifest_type": "build_snapshot",
        "git_commit": commit,
        "metadata_generated_at": generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "manifest_hash": manifest_hash(manifests),
        "hash_algorithm": "sha256",
        "hash_scope": sorted(manifests),
        "volatile_fields_excluded_from_hash": ["metadata_generated_at", "git_commit", "working_tree_dirty"],
        "working_tree_dirty": dirty,
        "scanner_version": MANIFEST_VERSION,
    }
    validate_manifest(snapshot, schema)
    manifests["build_snapshot.json"] = snapshot
    for name in sorted(manifests):
        write_json(output_dir / name, manifests[name])
    return manifests, audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate safe, code-backed CSR Judge metadata.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output or root / "frontend/public/judge/data/auto"
    manifests, audit = generate_all(root, output)
    print(json.dumps({
        "output": repository_relative(root, Path(output)),
        "files": sorted(manifests),
        "read_file_count": len(audit.read_paths),
        "manifest_hash": manifests["build_snapshot.json"]["manifest_hash"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
