import argparse
import json

from backend.config import ROOT
from backend.ai_api.app.domains.diagnosis.preflight import model_preflight


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", action="store_true", help="Save non-sensitive evidence inside this application")
    args = parser.parse_args()
    try:
        result = {"task": "P0-006", "passed": True, "ml": model_preflight().model_dump(mode="json"),
                  "paid_api_calls": 0, "conversational_inference": "NOT_IMPLEMENTED"}
    except Exception:
        result = {"task": "P0-006", "passed": False, "error": "ML_PREFLIGHT_FAILED", "paid_api_calls": 0}
    if args.record:
        output = ROOT / "docs/evidence/model_preflight.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
