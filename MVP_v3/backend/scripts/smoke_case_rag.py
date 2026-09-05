"""Read-only local DB/RAG smoke; optional ONE real AI request, no saved messages.

Run from MVP_v3 with PYTHONPATH=backend. --live-ai explicitly opts into a paid
call (max_calls=1, max_retries=0, concurrency=1, input<=6000 characters).
The AI server retains its configured output limit (default 400 tokens).
Never prints keys, customer record contents or the generated answer.
"""
import argparse
import asyncio
import json

from general_api.app import main
from general_api.app.clients.diagnosis_ai import HttpDiagnosisAiClient
from general_api.app.domains.cases.case_retrieval import collect_records, retrieve_context


async def run(case_id: str, live_ai: bool):
    repo = main.repository
    try:
        case = await repo.get(case_id)
        if not case:
            raise RuntimeError("Case not found")
        records = collect_records(case_id, messages=await repo.list_messages(case_id),
                                  questions=await repo.list_customer_questions(case_id),
                                  facts=await repo.list_case_facts(case_id),
                                  verifications=await repo.list_verifications(case_id),
                                  staff=await main.read_staff_context_records(case_id))
        context = retrieve_context(case_id, "송금 개인정보 고객 답변 확인 담당자 업무", records)
        assert context, "No matching case records: choose a case with saved questions or facts"
        result = {"db": "ok", "retrieval": "ok", "sources": len(context), "ai_calls": 0, "case_writes": 0}
        if live_ai:
            payload = {"case_id": case_id, "prompt": "검색 근거에서 이미 답변한 내용 하나와 아직 확인되지 않은 일 하나를 구분해 두 문장으로 답하세요.",
                       "retrieved_context": context, "assistant_mode": "BANK_INTERNAL"}
            assert len(json.dumps(payload, ensure_ascii=False)) <= 6000
            result["ai_calls"] = 1
            # Http client and model SDK each use zero retries for this path.
            response = await HttpDiagnosisAiClient(timeout_seconds=30).generate_case_copilot_reply(payload)
            assert response.get("content", "").strip(), "Empty AI response"
            assert "FALLBACK" not in response.get("model_mode", ""), "Not a real AI response"
            result["ai"] = "ok"
            result["model"] = response["model_mode"]
        print(json.dumps(result, ensure_ascii=True))
    finally:
        close = getattr(repo, "close", None)
        if close:
            await close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--live-ai", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.case_id, args.live_ai))
