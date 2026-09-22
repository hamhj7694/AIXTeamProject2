"""Ordered SQL discovery; persisted migration identity remains the basename."""
from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / 'migrations'


def ordered_migrations(directory: Path = MIGRATIONS_DIR) -> list[Path]:
    directory = directory.resolve()
    entries = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    if not isinstance(entries, list) or not entries:
        raise ValueError('Migration manifest must be a nonempty ordered list')
    paths = []
    names = set()
    for entry in entries:
        if not isinstance(entry, str):
            raise ValueError('Migration path must be a string')
        relative = PurePosixPath(entry)
        if (relative.is_absolute() or len(relative.parts) != 2
                or relative.parts[0] in ('.', '..', 'rollback')
                or '\\' in entry or ':' in entry
                or not re.fullmatch(r'\d{3}_[a-z0-9_]+\.sql', relative.name)):
            raise ValueError(f'Invalid forward migration path: {entry}')
        path = (directory / entry).resolve()
        if not path.is_relative_to(directory) or not path.is_file():
            raise ValueError(f'Missing or unsafe migration: {entry}')
        if path.name in names:
            raise ValueError(f'Duplicate migration identity: {path.name}')
        names.add(path.name)
        paths.append(path)
    discovered = {p.resolve() for p in directory.rglob('*.sql')
                  if p.relative_to(directory).parts[0] != 'rollback'}
    if discovered != set(paths):
        raise ValueError('Unlisted SQL files or duplicate paths in migration manifest')
    # Preserve the historical global ordering, including both 009 migrations.
    if [p.name for p in paths] != sorted(names):
        raise ValueError('Manifest must preserve global filename order')
    return paths


def migration_path(name: str) -> Path:
    for path in ordered_migrations():
        if path.name == name:
            return path
    raise ValueError(f'Unknown migration: {name}')
