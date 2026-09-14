from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .common import ScanAudit, evidence, read_text, repository_relative, source_line


def _compose_services(text: str) -> list[dict[str, Any]]:
    services: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    section: str | None = None
    in_services = False
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if indent == 0:
            in_services = stripped == "services:"
            current = None
            section = None
            continue
        if not in_services:
            continue
        service_match = re.match(r"^  ([A-Za-z0-9_-]+):$", line)
        if service_match:
            current = {
                "id": service_match.group(1), "image": None, "dockerfile": None,
                "ports": [], "volumes": [], "dependencies": [], "healthcheck": False,
                "environment_variables": [],
            }
            services.append(current)
            section = None
            continue
        if current is None:
            continue
        section_match = re.match(r"^    ([A-Za-z0-9_-]+):(?:\s*(.*))?$", line)
        if section_match:
            section = section_match.group(1)
            value = (section_match.group(2) or "").strip().strip('"\'')
            if section == "image" and value:
                current["image"] = value
            if section == "healthcheck":
                current["healthcheck"] = True
            continue
        if indent >= 6 and stripped.startswith("dockerfile:"):
            current["dockerfile"] = stripped.split(":", 1)[1].strip()
        elif indent >= 6 and section in {"ports", "volumes"} and stripped.startswith("-"):
            current[section].append(stripped[1:].strip().strip('"\''))
        elif indent == 6 and section == "depends_on" and stripped.endswith(":"):
            current["dependencies"].append(stripped[:-1])
        elif indent == 6 and section == "environment":
            key = stripped.split(":", 1)[0]
            if re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
                current["environment_variables"].append(key)
    for service in services:
        for key in ("ports", "volumes", "dependencies", "environment_variables"):
            service[key] = sorted(set(service[key]))
    return services


def _dockerfile(root: Path, path: Path, audit: ScanAudit) -> dict[str, Any]:
    text = read_text(path, audit)
    images = re.findall(r"^FROM\s+([^\s]+)(?:\s+AS\s+[^\s]+)?", text, flags=re.MULTILINE | re.IGNORECASE)
    ports = [int(value) for value in re.findall(r"^EXPOSE\s+(\d+)", text, flags=re.MULTILINE | re.IGNORECASE)]
    return {"source_path": repository_relative(root, path), "images": images, "exposed_ports": ports}


def scan_deployment(root: Path, audit: ScanAudit) -> dict[str, Any]:
    compose_path = root / "docker-compose.yml"
    nginx_path = root / "frontend/nginx.conf"
    compose_text = read_text(compose_path, audit)
    nginx_text = read_text(nginx_path, audit)
    dockerfiles = [
        _dockerfile(root, root / "frontend/Dockerfile", audit),
        _dockerfile(root, root / "backend/Dockerfile.general-api", audit),
        _dockerfile(root, root / "backend/Dockerfile.ai-api", audit),
    ]
    listen = re.search(r"\blisten\s+(\d+)", nginx_text)
    static_root = re.search(r"\broot\s+([^;]+);", nginx_text)
    proxy = re.search(r"proxy_pass\s+([^;]+);", nginx_text)
    fallback = re.search(r"try_files\s+([^;]+);", nginx_text)
    return {
        "services": _compose_services(compose_text),
        "dockerfiles": dockerfiles,
        "nginx": {
            "listen_port": int(listen.group(1)) if listen else None,
            "static_root": static_root.group(1).strip() if static_root else None,
            "api_proxy": proxy.group(1).strip() if proxy else None,
            "spa_fallback": fallback.group(1).strip() if fallback else None,
            "source_path": repository_relative(root, nginx_path),
        },
        "evidence": [
            evidence(repository_relative(root, compose_path), "Docker Compose services, dependencies, ports and volumes"),
            evidence(repository_relative(root, nginx_path), "Production static root, API proxy and SPA fallback", source_line(nginx_text, "root ")),
            *[evidence(item["source_path"], "Container runtime image and exposed port") for item in dockerfiles],
        ],
    }

