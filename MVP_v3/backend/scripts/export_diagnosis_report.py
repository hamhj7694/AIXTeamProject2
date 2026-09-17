"""Run one diagnosis and export a privacy-safe developer JSON report."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from ai_api.app.domains.diagnosis.service import DiagnosisService


def _safe_report(result: Any) -> dict[str, Any]:
    data = result.model_dump(mode="json")
    data.pop("turns", None)
    for event in data.get("events", []):
        event.pop("evidence_text", None)
    for evidence in data.get("evidence", []):
        evidence.pop("text", None)
    for window in data.get("windows", []):
        window.pop("text", None)
    return data


async def _run(text: str) -> dict[str, Any]:
    result = await DiagnosisService().analyze(text)
    return _safe_report(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export privacy-safe DiagnosisResult JSON")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="Transient text to analyze")
    source.add_argument("--input", type=Path, help="UTF-8 text file to analyze")
    parser.add_argument("--output", type=Path, default=Path("diagnosis-report.json"))
    args = parser.parse_args()
    text = args.text if args.text is not None else args.input.read_text(encoding="utf-8")
    report = asyncio.run(_run(text))
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    audit = report.get("semantic_audit") or {}
    print(json.dumps({
        "output": str(args.output),
        "audit_status": audit.get("audit_status"),
        "audit_score": audit.get("overall_score"),
        "semantic_atom_count": len(report.get("semantic_atoms", [])),
        "relation_count": len(report.get("semantic_relations", [])),
        "context_signal_count": len(report.get("context_signals", [])),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
