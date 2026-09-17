"""Measure v3.0 service-level OpenAI usage without mutating production or DB."""
from __future__ import annotations

import asyncio, datetime as dt, json, os, sys
from pathlib import Path
from types import SimpleNamespace

V30 = Path(os.environ["V30_WORKTREE"])
ROOT = Path(os.environ["BENCHMARK_ROOT"])
OUT = Path(os.environ["TOKEN_OUTPUT"])
sys.path.insert(0, str(V30 / "MVP_v3" / "backend"))

from openai import AsyncOpenAI as RealAsyncOpenAI
from ai_api.app.domains.diagnosis import extractor, context_features
from ai_api.app.domains.case_support import brief_service, copilot_service, work_card_service, final_report_service
from contracts.ai_internal.case_copilot import CaseCopilotInput
from contracts.ai_internal.work_card import CaseWorkCardInput
from contracts.ai_internal.final_report import FinalCaseReportInput
from contracts.diagnosis import DiagnosisResult, Evidence, WindowResult, RiskLevel

FIX = json.loads((ROOT / "token_benchmark" / "token_fixtures_v1.json").read_text(encoding="utf-8"))
TEXT = "\n".join(json.loads((ROOT / "fact_context_cases.json").read_text(encoding="utf-8"))["cases"][0]["turns"][i]["text"] for i in range(5))
USAGE: list[dict] = []

def usage_dict(u):
    if u is None: return {}
    out = {}
    for k in ("input_tokens", "output_tokens", "total_tokens"):
        v = getattr(u, k, None)
        if v is not None: out[k] = int(v)
    details = getattr(u, "input_tokens_details", None)
    if details is not None and getattr(details, "cached_tokens", None) is not None:
        out["cached_input_tokens"] = int(details.cached_tokens)
    return out

class TraceResponses:
    def __init__(self, owner): self.owner = owner
    async def create(self, **kwargs):
        response = await self.owner.client.responses.create(**kwargs)
        USAGE.append({"model": kwargs.get("model"), "usage": usage_dict(getattr(response, "usage", None)), "operation": kwargs.get("text", {}).get("format", {}).get("name", "responses.create")})
        return response

class TraceClient:
    def __init__(self, *args, **kwargs): self.client = RealAsyncOpenAI(*args, **kwargs); self.responses = TraceResponses(self)
    async def __aenter__(self): await self.client.__aenter__(); return self
    async def __aexit__(self, *args): return await self.client.__aexit__(*args)

for mod in (extractor, context_features, brief_service, copilot_service, work_card_service, final_report_service):
    mod.AsyncOpenAI = TraceClient

async def run_feature(feature: str) -> None:
    before = len(USAGE)
    if feature == "case_creation_diagnosis":
        ev = await extractor.extract_events(TEXT)
        ctx = await extractor.extract_context_from_signals(ev.events)
        # Brief construction is deterministic in v3.0; only the two calls above are counted.
        _ = ctx
    elif feature == "bank_staff_chat_ai":
        await copilot_service.CaseCopilotService().generate(CaseCopilotInput(case_id="TOKEN-01", prompt="현재 사건에서 우선 확인하고 조치할 사항을 알려줘.", case_summary="보이스피싱 의심 사건", known_facts=["기관 사칭", "이체 요구"]))
    elif feature in {"customer_confirmation_question_ai", "verification_ai", "action_work_ai"}:
        card = {"customer_confirmation_question_ai":"QUESTION_PLAN", "verification_ai":"VERIFICATION_REQUEST", "action_work_ai":"BANK_ACTION"}[feature]
        await work_card_service.CaseWorkCardService().generate(CaseWorkCardInput(case_id="TOKEN-01", card_type=card, case_summary="보이스피싱 의심 사건", known_facts=["기관 사칭", "이체 요구"], pending_verifications=["기관: 공식 채널 확인"]))
    elif feature == "customer_chat_ai":
        await copilot_service.CaseCopilotService().generate(CaseCopilotInput(case_id="TOKEN-01", prompt="제가 지금 무엇을 확인하고 어떻게 행동해야 하나요?", assistant_mode="CUSTOMER_SUPPORT", case_summary="고객 공개용 보이스피싱 의심 사건"))
    elif feature == "final_report_ai":
        await final_report_service.FinalCaseReportService().generate(FinalCaseReportInput(case_id="TOKEN-01", workflow_status="REVIEW", case_mode="PREVENT", case_summary="보이스피싱 의심 사건", known_facts=["기관 사칭", "이체 요구"], verification_results=["공식 확인 필요"], action_results=["상담 접수"]))
    else: raise ValueError(feature)
    calls = USAGE[before:]
    if not calls: raise RuntimeError(f"{feature}: no provider call observed")

async def main():
    runs=[]
    features=[f["feature"] for f in FIX["fixtures"]]
    for run in range(1, 4):
        for feature in features:
            start=len(USAGE); status="LIVE"; error=None
            try: await run_feature(feature)
            except Exception as exc: status="ERROR"; error=type(exc).__name__
            calls=USAGE[start:]
            totals={k:sum(c.get("usage",{}).get(k,0) for c in calls) for k in ("input_tokens","output_tokens","total_tokens","cached_input_tokens")}
            runs.append({"version":"v3.0","commit":"071fb512ce42a570b0bcf585041eac6f31c2fb1c","fixture_id":next(f["fixture_id"] for f in FIX["fixtures"] if f["feature"]==feature),"feature":feature,"run":run,"model":next((c["model"] for c in calls if c.get("model")),os.getenv("OPENAI_EVENT_MODEL","gpt-4o-mini")),**totals,"llm_call_count":len(calls),"status":status,"error":error})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/"token_usage_runs.json").write_text(json.dumps(runs,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (OUT/"token_usage_calls.json").write_text(json.dumps(USAGE,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"TOKEN_USAGE_COMPLETE","runs":len(runs),"calls":len(USAGE),"output":str(OUT)}))

if __name__ == "__main__": asyncio.run(main())
