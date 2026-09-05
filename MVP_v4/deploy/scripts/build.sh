#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$TASK_ROOT"
if [[ ! -x .venv/bin/python ]]; then
  python3.11 -m venv .venv
fi
.venv/bin/python -c 'import sys; assert sys.version_info[:2] == (3, 11), "Python 3.11 required"'
.venv/bin/python -m pip install --cache-dir .cache/pip -r backend/requirements.txt
.venv/bin/python -m scripts.verify_self_contained
.venv/bin/python -m scripts.verify_env_example
.venv/bin/python -m pytest tests -q
cd frontend
npm ci --cache ../.cache/npm
npm run typecheck
npm test
npm run build
test -f dist/index.html
test -d dist/assets
