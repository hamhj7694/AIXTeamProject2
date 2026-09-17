"""Schema validation, hashes, freeze manifest, and generic Atomic Fact scoring."""
from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = ["fact_context_cases.json", "chat_prompts.json", "question_states.json", "rag_queries.json", "e2e_cases.json"]

def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def load(name: str): return json.loads((ROOT / name).read_text(encoding="utf-8"))

def validate() -> dict:
    facts, chat, questions, rag, e2e = (load(name) for name in FILES)
    atomic = [f for case in facts["cases"] for f in case["atomic_facts"]]
    assert len(facts["cases"]) == 30 and len(atomic) >= 150
    assert len(chat["prompts"]) >= 20 and {"P-01", "P-02", "P-03", "P-04", "P-05"} <= {p["id"] for p in chat["prompts"]}
    assert len(questions["cases"]) >= 15 and len(e2e["cases"]) >= 10
    assert rag["status"] == "NOT_IMPLEMENTED" and not rag["queries"]
    required = {"semantic_key", "gold_value", "polarity", "criticality", "source_turn", "expected_visibility", "expected_panel_section"}
    assert all(required <= set(f) for f in atomic)
    return {"case_count": len(facts["cases"]), "gold_fact_count": len(atomic), "prompt_count": len(chat["prompts"]), "rag_query_count": len(rag["queries"]), "e2e_case_count": len(e2e["cases"])}

def freeze() -> None:
    counts = validate()
    hashes = {name: sha(ROOT / name) for name in FILES}
    manifest = {"benchmark_version": "benchmark_v1.0", "frozen_before_version_runs": True, "dataset_files": hashes,
                "evaluator_sha256": sha(Path(__file__)), **counts}
    (ROOT / "BENCHMARK_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "BENCHMARK_FROZEN").write_text("benchmark_v1.0\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("command", choices=["validate", "freeze"]); args = parser.parse_args()
    print(json.dumps(validate(), ensure_ascii=False, indent=2)) if args.command == "validate" else freeze()
