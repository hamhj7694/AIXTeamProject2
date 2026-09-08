from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .common import ScanAudit, evidence, read_json, read_text, repository_relative, source_line


FRONTEND_DEPENDENCIES = (
    "react", "react-dom", "react-router-dom", "lucide-react",
    "typescript", "vite", "@vitejs/plugin-react",
)


def scan_frontend(root: Path, audit: ScanAudit) -> dict[str, Any]:
    frontend = root / "frontend"
    package_path = frontend / "package.json"
    lock_path = frontend / "package-lock.json"
    vite_path = frontend / "vite.config.ts"
    app_path = frontend / "src" / "App.tsx"
    client_path = frontend / "src" / "api" / "client.ts"
    package = read_json(package_path, audit)
    lock = read_json(lock_path, audit)
    vite_text = read_text(vite_path, audit)
    app_text = read_text(app_path, audit)
    client_text = read_text(client_path, audit)

    package_source = repository_relative(root, package_path)
    lock_source = repository_relative(root, lock_path)
    technologies = []
    declared = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
    lock_packages = lock.get("packages", {})
    for name in FRONTEND_DEPENDENCIES:
        if name not in declared:
            continue
        locked = lock_packages.get(f"node_modules/{name}", {}).get("version")
        technologies.append({
            "name": name,
            "declared_version": declared[name],
            "resolved_version": locked,
            "scope": "frontend",
            "source_paths": [package_source, lock_source],
        })

    routes = sorted(set(re.findall(r'<Route\s+path=["\']([^"\']+)["\']', app_text)))
    polling = []
    for number, line in enumerate(app_text.splitlines(), start=1):
        if "setInterval" not in line:
            continue
        matches = re.findall(r",\s*(\d+)\s*\)", line)
        if matches:
            polling.append({"interval_ms": int(matches[-1]), "source_path": repository_relative(root, app_path), "line": number})
    for relative in ("src/pages/CaseRoomPage.tsx", "src/pages/CustomerCaseRoomPage.tsx", "src/components/EditableContext.tsx"):
        path = frontend / relative
        text = read_text(path, audit)
        for number, line in enumerate(text.splitlines(), start=1):
            if "setInterval" not in line:
                continue
            matches = re.findall(r",\s*(\d+)\s*\)", line)
            if matches:
                polling.append({"interval_ms": int(matches[-1]), "source_path": repository_relative(root, path), "line": number})

    port_match = re.search(r"port:\s*(\d+)", vite_text)
    proxy_match = re.search(r"target:\s*['\"]([^'\"]+)", vite_text)
    return {
        "technologies": technologies,
        "routes": routes,
        "polling": sorted(polling, key=lambda item: (item["source_path"], item["line"])),
        "build_command": package.get("scripts", {}).get("build"),
        "dev_server": {
            "port": int(port_match.group(1)) if port_match else None,
            "api_proxy_target": proxy_match.group(1) if proxy_match else None,
        },
        "api_base": {
            "environment_variable": "VITE_API_BASE_URL" if "VITE_API_BASE_URL" in client_text else None,
            "default": "same-origin" if "|| ''" in client_text else "unverified",
        },
        "public_directory": "frontend/public",
        "evidence": [
            evidence(package_source, "Frontend dependency and build scripts"),
            evidence(repository_relative(root, vite_path), "Vite development server and API proxy", source_line(vite_text, "server:")),
            evidence(repository_relative(root, app_path), "React routes and polling", source_line(app_text, "<Routes>")),
            evidence(repository_relative(root, client_path), "Same-origin API base with optional VITE_API_BASE_URL", source_line(client_text, "VITE_API_BASE_URL")),
        ],
    }

