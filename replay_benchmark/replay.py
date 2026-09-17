"""Read-only capability replay for a frozen CSR benchmark.

This runner intentionally does not call live AI, create a DB, or alter a
source tree.  It produces complete evidence skeletons and records whether a
metric is executable in the supplied version/environment.
"""
from __future__ import annotations

import argparse, csv, datetime as dt, json, os, platform, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
V30 = "071fb512ce42a570b0bcf585041eac6f31c2fb1c"

def command(*args: str, cwd: Path) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True, encoding="utf-8").strip()

def has(source: Path, relative: str, token: str = "") -> bool:
    path = source / relative
    return path.exists() and (not token or token in path.read_text(encoding="utf-8", errors="ignore"))

def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def main() -> None:
    p = argparse.ArgumentParser(); p.add_argument("run", choices=["run"]); p.add_argument("--label", required=True)
    p.add_argument("--source", type=Path, required=True); p.add_argument("--status", choices=["FINAL", "PRELIMINARY"], required=True)
    args = p.parse_args(); source = args.source.resolve(); out = ROOT / "results" / args.label; out.mkdir(parents=True, exist_ok=True)
    sha = command("git", "rev-parse", "HEAD", cwd=source); subject = command("git", "show", "-s", "--format=%s", "HEAD", cwd=source)
    date = command("git", "show", "-s", "--format=%ci", "HEAD", cwd=source)
    provider = bool(os.getenv("OPENAI_API_KEY")); docker_available = False
    features = {
        "case_creation": has(source, "MVP_v3/backend/general_api/app/main.py", "/api/cases/analyze"),
        "message_persistence": has(source, "MVP_v3/backend/general_api/app/main.py", "/messages"),
        "generic_message_fact_extraction": has(source, "MVP_v3/backend/ai_api/app/domains/case_support/context_fact_extraction_service.py"),
        "context_v2": has(source, "MVP_v3/backend/migrations/014_case_context_v2_foundation.sql"),
        "context_v3": has(source, "MVP_v3/backend/migrations/015_context_panel_v3.sql"),
        "case_local_rag": has(source, "MVP_v3/backend/general_api/app/domains/cases/case_retrieval.py"),
        "official_rag": False,
        "final_report_export": has(source, "MVP_v3/backend/general_api/app/main.py", "reports/final/export"),
    }
    manifest = {"label": args.label, "result_status": args.status, "git_sha": sha, "git_short_sha": sha[:7], "commit_subject": subject,
                "commit_date": date, "executed_at": dt.datetime.now(dt.timezone.utc).isoformat(), "python": sys.version,
                "platform": platform.platform(), "ai_provider_configured": provider, "docker_available": docker_available,
                "benchmark_manifest": json.loads((ROOT / "BENCHMARK_MANIFEST.json").read_text(encoding="utf-8")), "features": features}
    write_json(out / "manifest.json", manifest)
    dataset_hashes = manifest["benchmark_manifest"]["dataset_files"]
    (out / "dataset_hash.txt").write_text(json.dumps(dataset_hashes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "evaluator_hash.txt").write_text(manifest["benchmark_manifest"]["evaluator_sha256"] + "\n", encoding="utf-8")
    unavailable = {"status": "NOT RUN", "reason": "Live AI provider and isolated MySQL/Docker environment are unavailable."}
    for name in ("metrics.json", "hard_gates.json"):
        write_json(out / name, {"status": "STATIC_REPLAY_ONLY", "features": features, "live_measurement": unavailable})
    fields = ["case_id", "fact_id", "semantic_key", "gold_value", "criticality", "message_saved", "fact_extracted", "fact_correct", "evidence_linked", "polarity_correct", "context_present", "panel_present", "reload_present", "ai_context_present", "ai_answer_correct", "status", "reason"]
    for name in ("fact_results.csv", "chat_results.csv", "question_results.csv", "ml_results.csv", "rag_results.csv", "e2e_results.csv"):
        with (out / name).open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerow({"status": "NOT RUN", "reason": unavailable["reason"]})
    for name in ("raw_responses", "api_responses", "db_snapshots", "screenshots", "reports"):
        (out / name).mkdir(exist_ok=True)
        (out / name / "NOT_RUN.txt").write_text(unavailable["reason"] + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))

if __name__ == "__main__": main()
