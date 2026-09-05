#!/usr/bin/env bash
set -euo pipefail
curl --fail --silent --show-error http://127.0.0.1:8101/health
curl --fail --silent --show-error http://127.0.0.1:8100/api/v4/health
curl --fail --silent --show-error http://127.0.0.1/api/v4/health
# This is expected to fail until the AI engine is ported and configured.
curl --fail --silent --show-error http://127.0.0.1:8100/api/v4/ready
