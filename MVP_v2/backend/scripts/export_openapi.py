from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from general_api.app.main import app  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the General API OpenAPI contract.")
    parser.add_argument("--output", required=True, help="Output JSON path")
    args = parser.parse_args()

    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"General API OpenAPI exported to {output}")


if __name__ == "__main__":
    main()
