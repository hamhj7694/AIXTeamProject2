"""External-environment AI smoke/replay runner.

It intentionally writes only sanitized structured outputs.  API keys and raw
credentials are never written.  Full scored KPI calculation remains subject to
the frozen evaluator and available gold-to-output mappings.
"""
from __future__ import annotations

import argparse, asyncio, datetime as dt, hashlib, json, os, subprocess, sys
from pathlib import Path

EXPECTED = "071fb512ce42a570b0bcf585041eac6f31c2fb1c"

def main() -> None:
    p = argparse.ArgumentParser(); p.add_argument("--v30", type=Path, required=True); p.add_argument("--benchmark", type=Path, required=True); p.add_argument("--output", type=Path, required=True); a = p.parse_args()
    head = subprocess.check_output(["git", "-c", f"safe.directory={a.v30}", "-C", str(a.v30), "rev-parse", "HEAD"], text=True).strip()
    if head != EXPECTED: raise SystemExit(f"v3.0 SHA mismatch: {head}")
    sys.path.insert(0, str(a.v30 / "MVP_v3" / "backend"))
    from ai_api.app.domains.diagnosis.extractor import extract_events
    cases = json.loads((a.benchmark / "fact_context_cases.json").read_text(encoding="utf-8"))["cases"]
    a.output.mkdir(parents=True, exist_ok=True)
    rows = []
    for case in cases:
        text = "\n".join(item["text"] for item in case["turns"])
        try:
            result = asyncio.run(extract_events(text))
            rows.append({"case_id": case["case_id"], "status": "LIVE", "extractor_model": result.extractor_model,
                         "event_count": len(result.events), "successful_turn_ids": result.successful_turn_ids,
                         "warning_count": len(result.warnings), "events": [e.model_dump(mode="json") for e in result.events]})
        except Exception as exc:
            rows.append({"case_id": case["case_id"], "status": "ERROR", "error_type": type(exc).__name__})
    payload = {"status": "LIVE_AI_READY", "executed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
               "v30_commit": head, "case_count": len(cases), "api_key_logged": False, "cases": rows}
    (a.output / "runtime_status.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "case_count": len(cases), "output": str(a.output)}, ensure_ascii=False))

if __name__ == "__main__": main()
