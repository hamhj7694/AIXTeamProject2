"""Structured Case Brief용 OpenAI prompt.

이 prompt는 Diagnosis가 이미 확정한 위험도/증거를 다시 판단하지 않는다.
"""
from __future__ import annotations

import json

from contracts.ai_internal.mvp_workflow import CaseBrief
from contracts.diagnosis import DiagnosisResult


CASE_BRIEF_PROMPT_VERSION = "mvp_v1"

CASE_BRIEF_OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
    },
    "required": ["summary"],
}


def build_case_brief_prompt(diagnosis: DiagnosisResult, brief: CaseBrief) -> tuple[str, str]:
    """LLM에는 검증된 입력만 주고, 담당자용 요약 문장만 보강하게 한다."""
    instructions = """당신은 보이스피싱 공동대응 담당자를 돕는 요약 도우미입니다.
주어진 Diagnosis와 결정론적으로 만든 CaseBrief만 사용해 담당자용 한국어 summary를 작성하세요.
입력에 없는 기관명, 인물, 금액, 계좌, 법적 사실, 금융 조치나 최종 사기 판정을 만들지 마세요.
불확실한 내용은 단정하지 말고 '확인 필요'로 표현하세요. 위험도와 점수는 재판단하지 마세요.
반드시 JSON schema에 맞춰 출력하세요."""
    payload = {
        "prompt_version": CASE_BRIEF_PROMPT_VERSION,
        "diagnosis": {
            "summary": diagnosis.context.summary,
            "incident_type": diagnosis.context.incident_type,
            "claims": diagnosis.context.claims,
            "risk_level": diagnosis.risk_level.value,
            "risk_score": diagnosis.risk_score,
            "evidence": [item.model_dump() for item in diagnosis.evidence],
            "requested_amount_max": diagnosis.features.get("requested_amount_max"),
        },
        "deterministic_brief": brief.model_dump(mode="json"),
    }
    return instructions, json.dumps(payload, ensure_ascii=False)
