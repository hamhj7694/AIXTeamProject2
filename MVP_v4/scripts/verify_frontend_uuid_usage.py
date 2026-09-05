import json

from scripts.verify_self_contained import ROOT, audit

if __name__ == "__main__":
    issues = [v for v in audit()["violations"] if v["rule"] == "direct_uuid_outside_helper"]
    helper_exists = (ROOT / "frontend/src/shared/uuid.ts").is_file()
    result = {"passed": helper_exists and not issues, "helper_exists": helper_exists, "direct_uuid_uses_outside_helper": len(issues)}
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
