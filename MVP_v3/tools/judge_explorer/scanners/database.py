from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .common import ScanAudit, evidence, read_text, repository_relative


TABLE_PATTERN = re.compile(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?([A-Za-z0-9_]+)`?", re.IGNORECASE)
TRIGGER_PATTERN = re.compile(r"CREATE\s+TRIGGER\s+`?([A-Za-z0-9_]+)`?", re.IGNORECASE)


def scan_database(root: Path, audit: ScanAudit) -> dict[str, Any]:
    base_path = root / "database/01_mysql_csr_schema.sql"
    base_text = read_text(base_path, audit)
    migrations = []
    all_tables = set(TABLE_PATTERN.findall(base_text))
    all_triggers = set(TRIGGER_PATTERN.findall(base_text))
    migration_dir = root / "backend/migrations"
    for path in sorted(migration_dir.glob("*.sql"), key=lambda item: item.name):
        text = read_text(path, audit)
        tables = sorted(set(TABLE_PATTERN.findall(text)))
        triggers = sorted(set(TRIGGER_PATTERN.findall(text)))
        all_tables.update(tables)
        all_triggers.update(triggers)
        migrations.append({
            "name": path.name,
            "source_path": repository_relative(root, path),
            "created_tables": tables,
            "trigger_count": len(triggers),
            "has_alter_table": bool(re.search(r"\bALTER\s+TABLE\b", text, re.IGNORECASE)),
        })
    markers = sorted(set(re.findall(r"\('([^']+\.sql)'\)", base_text)))
    marker_gaps = sorted(item["name"] for item in migrations if item["name"] not in markers)
    return {
        "engine": "MySQL",
        "base_schema": repository_relative(root, base_path),
        "tables": sorted(all_tables),
        "table_count": len(all_tables),
        "migrations": migrations,
        "migration_count": len(migrations),
        "base_schema_migration_markers": markers,
        "marker_gaps": marker_gaps,
        "trigger_count": len(all_triggers),
        "evidence": [
            evidence(repository_relative(root, base_path), "New database baseline schema and migration markers"),
            evidence("backend/migrations/", "Additive migration files discovered by filename"),
        ],
    }

