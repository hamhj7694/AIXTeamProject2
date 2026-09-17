"""Corrected-gold audit evaluator for preserved v3.0 raw context outputs.

Only canonical facts with an explicit v3.0 projection are scored. Facts whose
target/status is not representable by the v3.0 output contract are reported as
non-comparable instead of being silently counted as misses.
"""
from __future__ import annotations
import hashlib, json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT / "MVP_v3/docs/now_md/A_part/A파트 테스트 및 파이프라인 구조 정리/fixtures/official_gold"
RAW = ROOT / "tests/context_test/baseline_v1/raw_results.json"
OUT = ROOT / "MVP_v3/tests/context_test/run_gold_v2"

COMPARABLE = {
    "crime_involvement_claim": ("claim_codes", "CLAIM_CRIME_INVOLVEMENT"),
    "auth_code_disclosure_requested": ("requested_action_codes", "REQUEST_AUTH_INFO"),
    "transfer_requested_or_instructed": ("requested_action_codes", "REQUEST_TRANSFER"),
    "safe_account_destination_claimed": ("requested_action_codes", "PURPOSE_SAFE_ACCOUNT"),
    "urgency": ("manipulation_tactic_codes", "TACTIC_URGENCY"),
}

def load(name): return json.loads((GOLD / name).read_text(encoding="utf-8"))
def profile():
    d=json.loads((ROOT/"replay_benchmark/fact_context_cases.json").read_text(encoding="utf-8")); groups=defaultdict(list); classes=Counter(); turns=0
    for c in d["cases"]:
        seq=[x["text"] for x in c["turns"]]; h=hashlib.sha256(json.dumps(seq,ensure_ascii=False,separators=(",",":")).encode()).hexdigest(); groups[h].append(c["case_id"]); classes[c["scenario_class"]]+=1; turns+=len(seq)
    return {"case_count":len(d["cases"]),"turn_count":turns,"unique_turn_sequence_count":len(groups),"scenario_class_counts":dict(classes),"sequences":[{"sequence_hash":h,"member_case_ids":ids,"member_count":len(ids)} for h,ids in groups.items()]}

def project(record):
    p=record.get("C_llm_payload",{}).get("case_context_features",{})
    return {k:set(p.get(k,[])) for k in ("claim_codes","requested_action_codes","manipulation_tactic_codes")}

def main():
    canonical={c["case_id"]:c for c in load("FACT_CONTEXT_CANONICAL_HUMAN_GOLD_v1.json")["cases"]}
    corrected={c["case_id"]:c for c in load("FACT_CONTEXT_GOLD_v3_0_CORRECTED.json")["cases"]}
    raw=json.loads(RAW.read_text(encoding="utf-8"))["records"]
    rows=[]; counts=Counter(); comparable_expected=0; comparable_hit=0
    for r in raw:
        cid=r["sample_id"].replace("S","FACT-") if r["sample_id"].startswith("S") else r["sample_id"]
        # preserved baseline uses S01..S30; canonical uses FACT-01..FACT-30
        cid=f"FACT-{int(r['sample_id'][1:]):02d}"
        gold=canonical[cid]["canonical_summary"]; out=project(r); case={"case_id":cid,"comparable":{},"non_comparable":[]}
        for key, val in gold.items():
            if key not in COMPARABLE:
                if val["knowledge_status"]=="OBSERVED": case["non_comparable"].append(key)
                continue
            field, code=COMPARABLE[key]; expected=val["knowledge_status"]=="OBSERVED"; found=code in out[field]
            case["comparable"][key]={"expected":expected,"found":found,"knowledge_status":val["knowledge_status"]}
            comparable_expected += int(expected); comparable_hit += int(expected and found)
            if expected and found: counts["tp"]+=1
            elif expected and not found: counts["fn"]+=1
            elif not expected and found: counts["fp"]+=1
            else: counts["tn"]+=1
        rows.append(case)
    p=profile(); precision=counts["tp"]/(counts["tp"]+counts["fp"]) if counts["tp"]+counts["fp"] else None; recall=comparable_hit/comparable_expected if comparable_expected else None; f1=2*precision*recall/(precision+recall) if precision is not None and recall else None
    metrics={"metric_version":"corrected_gold_v2_projection_audit","v3_0":{"status":"FULL_30_CASE_SCORE","case_count":len(rows),"sample_weighted":{"canonical_comparable_recall":recall,"canonical_comparable_precision":precision,"canonical_comparable_f1":f1,"tp":counts["tp"],"fp":counts["fp"],"fn":counts["fn"],"tn":counts["tn"],"comparable_expected":comparable_expected},"unique_sequence_weighted":"NOT_RUN","non_comparable_observed_fact_keys":sorted({k for x in rows for k in x["non_comparable"]})},"v3_1":{"status":"NOT_RUN","reason":"No v3.1 30-case raw result artifact found"},"historical_baseline_v1":"PRESERVED_ARCHIVE_ONLY","hard_gates":{"status":"NOT_RUN","reason":"This projection audit does not reconstruct all safety gates"},"dataset_profile":p}
    OUT.mkdir(parents=True,exist_ok=True); (OUT/"dataset_profile.json").write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); (OUT/"case_results.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); (OUT/"metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(json.dumps(metrics,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
