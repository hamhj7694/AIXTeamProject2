"""Structured Case Brief용 OpenAI prompt.

이 prompt는 Diagnosis가 이미 확정한 위험도/증거를 다시 판단하지 않는다.
"""
from __future__ import annotations

import json

from contracts.ai_internal.mvp_workflow import CaseBrief
from contracts.diagnosis import DiagnosisResult


CASE_BRIEF_PROMPT_VERSION = "current_case_snapshot_v3"

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
    instructions = """당신은 보이스피싱 대응 사건의 '현재 전체 상황 요약(Current Case Snapshot)'을 작성하는 요약 도우미입니다.
은행 담당자가 우측 Context Panel을 열었을 때 현재 사건의 가장 중요하고 최신인 상태를 10초 안에 이해할 수 있도록, 입력으로 제공된 전체 사건 정보를 바탕으로 하나의 자연스러운 한국어 문단을 작성하세요.

[작성 우선순위]
1. 현재 사건의 핵심 위험 상황: 사칭·기망 유형과 송금, 개인정보·인증정보, 원격앱 설치, 연락 차단·고립 등 중요한 위험행위를 우선합니다.
2. 현재까지 확인된 핵심 사실: 실제 발화, 고객 진술, 공식 확인 결과를 사용하며 최근 정보가 과거 정보보다 우선합니다.
3. 고객 피해·노출 상태: 실제 송금, 개인정보·인증정보 제공, 앱 설치 여부를 포함하되 확인되지 않은 내용은 절대 사실처럼 단정하지 않습니다.
4. 가장 중요한 미확인 사항 또는 다음 확인 포인트는 사건 대응에 필요한 것만 최대 1~2개 언급합니다.

[사실 상태 표현]
- 고객 답변은 '고객은 ~라고 답했습니다'처럼 출처를 보존합니다.
- 상대방의 주장은 상대방의 주장으로, 직원 메모는 직원 기록으로 표현합니다.
- 레거시 Fact 상태값만으로 내용을 사실이나 공식 확인으로 표현하지 않습니다.
- 공식 확인은 실제 근거 출처가 입력된 경우에만 표시합니다.
- REQUESTED/INSTRUCTED는 '요구했다', '지시했다', '유도했다'로 표현하며 고객이 실제 수행한 것으로 바꾸지 않습니다.
- COMPLETED는 실제 완료 근거가 있을 때만 '송금했다', '제공했다', '설치했다'라고 씁니다.

[출력 규칙]
- 3~4문장, 약 180~350자 분량의 하나의 문단만 출력합니다.
- 모든 Fact를 나열하지 말고 중요도와 최신성이 낮은 정보는 생략합니다.
- 명사 나열, 기계적인 필드 이어 붙이기, 같은 의미의 반복, '~정황으로 파악됩니다' 반복을 피합니다.
- '보이스피싱 의심', '상대방', '파악됩니다' 같은 표현을 반복하지 않습니다.
- 사건번호, 인명, 기관명, 금액 등 구체값은 입력에 실제로 있는 경우에만 사용합니다.
- 입력에 없는 기관명, 인물, 금액, 계좌, 법적 사실, 금융 조치나 최종 사기 판정을 만들지 않습니다.
- DB field 이름, semantic key, status enum 등 내부 용어를 노출하지 않습니다.
- 제목, bullet, JSON, 설명을 summary 안에 넣지 말고 문단 본문만 작성합니다.

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
