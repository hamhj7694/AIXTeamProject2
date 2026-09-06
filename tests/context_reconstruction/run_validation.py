"""Runtime validation for transcript -> features -> ML -> LLM Case Brief.

This is test-only code. It imports the MVP_v3 production services and never
writes a validation case to the production repository/database.
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import re
import sys
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
MVP = ROOT / "MVP_v3"
BACKEND = MVP / "backend"
RESULT_DIR = ROOT / "results" / "context_reconstruction"
FIGURE_DIR = RESULT_DIR / "figures"
DOCS_DIR = ROOT / "docs"
SAMPLES_PATH = ROOT / "tests" / "context_reconstruction" / "test_samples.json"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
load_dotenv(MVP / ".env", override=False)

from ai_api.app.domains.diagnosis.extractor import signal_context_payload  # noqa: E402
from ai_api.app.domains.diagnosis.features import features_from_events  # noqa: E402
from ai_api.app.domains.diagnosis.model_adapter import load_model_bundle  # noqa: E402
from ai_api.app.domains.diagnosis.service import DiagnosisService  # noqa: E402
from contracts.diagnosis import CaseContextFeatures  # noqa: E402
from general_api.app.domains.cases.initial_report import InitialReportBuilder  # noqa: E402
from general_api.app.domains.cases.signal_projection import project_diagnosis_for_case  # noqa: E402


CONTEXT_CODE_LABELS = {
    "ROLE_PROSECUTION": "검찰·수사기관 사칭",
    "ROLE_POLICE": "경찰 사칭",
    "ROLE_BANK": "은행 사칭",
    "ROLE_FAMILY": "가족 사칭",
    "ROLE_SUPPORT": "고객지원·수리센터 사칭",
    "CLAIM_CRIME_INVOLVEMENT": "범죄 연루 주장",
    "CLAIM_ACCOUNT_VERIFICATION": "계좌 검증 주장",
    "CLAIM_DEVICE_BROKEN": "기기 고장 주장",
    "CLAIM_UNAUTHORIZED_PAYMENT": "미승인 결제 주장",
    "CLAIM_LOAN_APPROVAL": "대출 승인 주장",
    "PURPOSE_SAFE_ACCOUNT": "안전계좌 명목",
    "PURPOSE_LOAN_REPAYMENT": "대출 상환 명목",
    "PURPOSE_REPAIR": "수리 명목",
    "PURPOSE_REFUND": "환불 명목",
    "REQUEST_TRANSFER": "송금 요구",
    "REQUEST_INSTALL_APP": "앱 설치 요구",
    "REQUEST_AUTH_INFO": "인증정보 요구",
    "REQUEST_PERSONAL_INFO": "개인정보 요구",
    "REQUEST_KEEP_CALL": "통화 유지 요구",
    "REQUEST_SECRECY": "비밀 유지 요구",
    "DEADLINE_TODAY": "오늘 기한",
    "DEADLINE_IMMEDIATE": "즉시 기한",
    "TACTIC_FEAR": "공포 유발",
    "TACTIC_URGENCY": "긴급성 압박",
    "TACTIC_ISOLATION": "고립 유도",
    "CUSTOMER_TRANSFERRED": "고객 송금 완료",
    "CUSTOMER_NOT_TRANSFERRED": "고객 미송금",
    "CUSTOMER_PROVIDED_AUTH": "고객 인증정보 제공",
    "CUSTOMER_PROVIDED_PERSONAL_INFO": "고객 개인정보 제공",
    "CUSTOMER_INSTALLED_APP": "고객 앱 설치",
    "NORMAL_DEPOSIT_CONSULTATION": "정상 예금·은행 상담",
    "NORMAL_CARD_CONSULTATION": "정상 카드 상담",
    "NORMAL_DAILY_CALL": "정상 일상 통화",
}

CONTEXT_GROUPS = {
    "ROLE_": "사칭 주체",
    "CLAIM_": "범죄자 주장",
    "PURPOSE_": "요구 목적",
    "REQUEST_": "행동 요구",
    "DEADLINE_": "긴급성",
    "TACTIC_": "심리 압박",
    "CUSTOMER_": "피해·행동 상태",
    "NORMAL_": "정상 맥락",
}

CONTEXT_FIELDS = [
    ("claimed_actor_types", "사칭 주체 코드 목록", "list[str]", "ROLE_ 관찰 중 부인되지 않은 코드", "활성 코드만"),
    ("claim_codes", "범죄자 주장 코드 목록", "list[str]", "CLAIM_ 관찰 중 부인되지 않은 코드", "활성 코드만"),
    ("requested_action_codes", "행동 요구 코드 목록", "list[str]", "REQUEST_ 관찰 중 부인되지 않은 코드", "활성 코드만"),
    ("manipulation_tactic_codes", "심리 조작 코드 목록", "list[str]", "TACTIC_ 관찰 중 부인되지 않은 코드", "활성 코드만"),
    ("exposure_risk_codes", "노출 위험 코드 목록", "list[str]", "독립 Extractor 경로에서는 기본 빈 목록", "빈 목록도 전달"),
    ("amount_values_krw", "금액 목록(원)", "list[float]", "독립 Extractor 경로에서는 기본 빈 목록", "빈 목록도 전달"),
    ("chronology", "턴별 관찰 연대기", "list[str]", "T{turn}:{status}:{code}", "활성·부인 관찰"),
    ("unknown_fields", "추가 확인 필요 필드", "list[str]", "독립 Extractor 경로에서는 기본 빈 목록", "빈 목록도 전달"),
    ("source", "구조화 입력 출처", "string", "항상 STRUCTURED_CONTEXT_FEATURES_ONLY", "항상 전달"),
    ("schema_version", "Context 스키마 버전", "string", "현재 case_context_features.v2", "항상 전달"),
    ("observations", "상태·턴 포함 전체 관찰", "list[object]", "code, turn, status 객체", "활성·부인 관찰"),
    ("extraction_method", "추출 방식", "string", "현재 LLM_INDEPENDENT", "항상 전달"),
]

SIGNAL_FIELDS = [
    ("signals[].signal", "사용자 표시용 신호 라벨", "string", "event를 privacy-safe 라벨로 변환"),
    ("signals[].event_family", "이벤트 대분류", "enum", "IMPERSONATION 등 5개 family"),
    ("signals[].subtype", "이벤트 세부 유형", "string|null", "각 family subtype"),
    ("signals[].impersonation_group", "사칭 그룹", "string|null", "공공기관·금융기관·가족 등"),
    ("signals[].turn", "발견 턴", "integer", "원문 대신 턴 번호"),
    ("signals[].amount_krw", "이벤트 금액", "number", "금액이 있을 때만 조건부 전달"),
    ("signals[].is_requested", "요구 여부", "boolean", "값이 있을 때만 조건부 전달"),
]

FEATURE_BASE_UNIVERSE = {
    "imp_present", "imp_public", "imp_financial", "imp_family", "imp_acquaintance",
    "imp_telecom", "imp_delivery_logistics", "imp_other", "imp_prosecution", "imp_police",
    "imp_fss", "imp_court", "imp_post_office", "imp_government_other", "imp_bank",
    "imp_card_company", "imp_loan_company", "imp_capital_company", "imp_savings_bank",
    "imp_financial_other", "imp_family_subtype", "imp_acquaintance_subtype",
    "imp_telecom_subtype", "imp_delivery_subtype", "imp_other_subtype",
}


def _context_group(code: str) -> str:
    return next((label for prefix, label in CONTEXT_GROUPS.items() if code.startswith(prefix)), "기타")


def _feature_category(name: str) -> str:
    if name.startswith("imp_"):
        return "사칭 주체"
    if name.startswith("strategy_"):
        if "urgency" in name:
            return "긴급성"
        if "fear" in name:
            return "공포"
        if "isolation" in name:
            return "고립 유도"
        return "심리 압박"
    if name.startswith("action_"):
        if "info" in name:
            return "개인정보·인증정보 요구"
        return "행동 요구"
    if name.startswith("money_"):
        return "금전 요구"
    if name.startswith("amount_") or "amount" in name:
        return "금액"
    if name.startswith("ix_"):
        return "상호작용"
    if name == "signal_family_count":
        return "신호 집계"
    return "기타"


def _feature_meaning(name: str) -> str:
    tokens = {
        "imp": "사칭", "strategy": "심리전략", "action": "행동요구", "money": "금전이동",
        "present": "존재", "repeat": "반복", "accel": "가속", "tri": "삼각 누적",
        "count": "횟수", "qc": "품질확인", "diversity": "유형 다양성", "event": "이벤트",
        "raw": "원시", "public": "공공기관", "financial": "금융기관", "family": "가족",
        "acquaintance": "지인", "telecom": "통신사", "delivery": "배송", "logistics": "물류",
        "other": "기타", "prosecution": "검찰", "police": "경찰", "fss": "금융감독원",
        "court": "법원", "post": "우체국", "office": "기관", "government": "정부기관",
        "bank": "은행", "card": "카드사", "company": "회사", "loan": "대출업체",
        "capital": "캐피탈", "savings": "저축은행", "subtype": "세부유형", "group": "그룹",
        "authority": "권위", "fear": "공포", "urgency": "긴급성", "legitimacy": "정당성",
        "info": "정보", "extraction": "탈취", "isolation": "고립", "request": "요구",
        "benefit": "이익", "resistance": "저항", "handling": "무마", "behavior": "행동",
        "control": "통제", "sensitive": "민감정보", "auth": "인증정보", "device": "기기",
        "contact": "접촉", "restriction": "제한", "handover": "전달", "account": "계좌",
        "rental": "대여", "high": "고위험", "risk": "위험", "movement": "이동",
        "transfer": "이체", "withdrawal": "인출", "cash": "현금", "fee": "수수료",
        "payment": "납부", "repayment": "상환", "mentioned": "언급", "requested": "요구됨",
        "max": "최대", "sum": "합계", "log1p": "로그변환", "signal": "신호",
        "family": "패밀리", "ix": "상호작용",
    }
    return " ".join(tokens.get(part, part) for part in name.split("_"))


def _value_shape(name: str) -> str:
    if name.endswith("_present") or name.startswith("imp_") and not name.endswith(("_count_raw_qc", "_diversity_qc")):
        return "0/1"
    if "amount" in name and "log1p" not in name and not name.endswith(("_present", "_repeat", "_count_qc", "_accel_tri")):
        return "number (KRW)"
    if "count" in name or "repeat" in name or "diversity" in name or "accel" in name:
        return "integer"
    return "number"


def build_inventory() -> pd.DataFrame:
    candidate_names = list(features_from_events([]).keys())
    bundle = load_model_bundle()
    model_features = set(bundle["model_features"])
    rows: list[dict[str, Any]] = []
    for name in candidate_names:
        rows.append({
            "대분류": _feature_category(name), "실제 Feature/Field명": name,
            "한국어 의미": _feature_meaning(name), "값 형태": _value_shape(name),
            "어떤 정보인가": "Window 이벤트에서 계산되는 숫자 후보 Feature",
            "Extractor 후보": "O", "ML 입력 여부": "O" if name in model_features else "X",
            "LLM 입력 여부": "X", "전달 규칙": "ML 선택 목록이면 0도 전달",
            "자연어 생성 시 사용 예": "직접 사용 안 함",
        })
    for field, meaning, shape, info, rule in CONTEXT_FIELDS:
        rows.append({
            "대분류": "LLM 구조화 Context", "실제 Feature/Field명": f"case_context_features.{field}",
            "한국어 의미": meaning, "값 형태": shape, "어떤 정보인가": info,
            "Extractor 후보": "Context Extractor", "ML 입력 여부": "X", "LLM 입력 여부": "O",
            "전달 규칙": rule, "자연어 생성 시 사용 예": f"{meaning}을 근거로 요약·주장·요구를 생성",
        })
    for path, meaning, shape, info in SIGNAL_FIELDS:
        rows.append({
            "대분류": "LLM 이벤트 Context", "실제 Feature/Field명": path,
            "한국어 의미": meaning, "값 형태": shape, "어떤 정보인가": info,
            "Extractor 후보": "Event Extractor", "ML 입력 여부": "X", "LLM 입력 여부": "O",
            "전달 규칙": "활성 이벤트만 전달", "자연어 생성 시 사용 예": "활성 신호의 맥락을 자연어로 요약",
        })
    return pd.DataFrame(rows)


def _active_context_codes(context: dict[str, Any]) -> list[str]:
    return sorted({str(item.get("code")) for item in context.get("observations", []) if item.get("code")})


def _active_numeric_features(features: dict[str, float]) -> list[str]:
    return sorted(name for name, value in features.items() if float(value or 0) != 0)


def _set_metrics(expected: set[Any], actual: set[Any]) -> tuple[float, float]:
    recall = len(expected & actual) / len(expected) if expected else float(actual == set())
    precision = len(expected & actual) / len(actual) if actual else float(expected == set())
    return recall, precision


def _amount_metrics(expected: list[float], actual: list[float]) -> tuple[float, float, bool]:
    exp = {round(float(v)) for v in expected}
    act = {round(float(v)) for v in actual if v is not None}
    recall, precision = _set_metrics(exp, act)
    return recall, precision, exp == act


def _normalize(text: str) -> str:
    return re.sub(r"[^0-9가-힣a-zA-Z]", "", str(text)).lower()


def _fact_match(fact: str, text: str) -> bool:
    target = _normalize(text)
    amount_tokens = re.findall(r"\d[\d,]*(?:\.\d+)?\s*(?:억|천만|백만|만|천)?원", fact)
    if amount_tokens and not all(_normalize(token) in target for token in amount_tokens):
        return False
    keyword_groups = [
        ["검찰"], ["경찰"], ["은행"], ["카드사", "카드"], ["가족", "동생", "엄마"],
        ["금융감독원", "금감원"], ["우체국"], ["택배", "배송"], ["고객지원", "수리센터"],
        ["송금", "이체", "보내"], ["인출", "현금"], ["otp", "인증번호", "인증정보"],
        ["개인정보", "주민등록번호", "계좌번호", "주소"], ["앱", "원격"],
        ["비밀", "알리지", "숨기"], ["통화", "끊지"], ["범죄", "사건", "연루"],
        ["고장"], ["결제"], ["대출", "상환"], ["오늘", "즉시", "지금", "분"],
        ["이미", "완료", "제공", "보냈"], ["않", "미송금", "거절", "필요없"],
        ["공식", "영업점"], ["정상"], ["카드전달", "카드를", "체크카드"],
    ]
    relevant = [group for group in keyword_groups if any(_normalize(word) in _normalize(fact) for word in group)]
    if relevant:
        return all(any(_normalize(word) in target for word in group) for group in relevant)
    tokens = [token for token in re.findall(r"[가-힣a-zA-Z]{2,}", fact) if token not in {"정황", "요구", "주장", "안내"}]
    return bool(tokens) and sum(_normalize(token) in target for token in tokens) / len(tokens) >= 0.5


def _brief_metrics(sample: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    brief = " ".join([
        context.get("summary", ""), context.get("incident_type", ""),
        *context.get("claims", []), *context.get("demands", []),
        *context.get("manipulation_tactics", []),
    ])
    critical = sample.get("critical_facts", [])
    forbidden = sample.get("forbidden_facts", [])
    preserved = [fact for fact in critical if _fact_match(fact, brief)]
    contradicted = [fact for fact in forbidden if _fact_match(fact, brief)]
    expected_amounts = {round(float(value)) for value in sample.get("amounts_krw", [])}
    mentioned_amounts = set()
    compact = brief.replace(",", "")
    for number, unit in re.findall(r"(\d+(?:\.\d+)?)\s*(억|천만|백만|만|천)?원", compact):
        multiplier = {"억": 100_000_000, "천만": 10_000_000, "백만": 1_000_000, "만": 10_000, "천": 1_000, "": 1}[unit or ""]
        mentioned_amounts.add(round(float(number) * multiplier))
    unsupported_amounts = sorted(mentioned_amounts - expected_amounts)
    output_concepts = set()
    for code, label in CONTEXT_CODE_LABELS.items():
        if _fact_match(label, brief):
            output_concepts.add(code)
    expected_codes = set(sample.get("expected_context_codes", []))
    supported_concepts = output_concepts & expected_codes
    hallucinated_concepts = output_concepts - expected_codes
    fact_precision = len(supported_concepts) / len(output_concepts) if output_concepts else 1.0
    return {
        "critical_fact_recall": len(preserved) / len(critical) if critical else 1.0,
        "critical_facts_preserved": preserved,
        "critical_facts_missing": [fact for fact in critical if fact not in preserved],
        "contradiction_count": len(contradicted), "contradicted_forbidden_facts": contradicted,
        "hallucination_count": len(hallucinated_concepts) + len(unsupported_amounts),
        "hallucinated_context_codes": sorted(hallucinated_concepts),
        "unsupported_amounts_krw": unsupported_amounts,
        "fact_precision": fact_precision,
        "amount_preservation": expected_amounts.issubset(mentioned_amounts) if expected_amounts else len(mentioned_amounts) == 0,
    }


async def _analyze_one(service: DiagnosisService, sample: dict[str, Any]) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    try:
        diagnosis = await service.analyze(sample["transcript"], case_id=f"validation-{sample['sample_id'].lower()}")
        payload = signal_context_payload(diagnosis.events)
        payload["case_context_features"] = diagnosis.case_context_features.model_dump(mode="json")
        model_features = list(load_model_bundle()["model_features"])
        selected = {name: float(diagnosis.features.get(name, 0) or 0) for name in model_features}
        safe = project_diagnosis_for_case(diagnosis)
        initial_report = InitialReportBuilder().build(f"validation-{sample['sample_id'].lower()}", safe)
        context_dict = diagnosis.case_context_features.model_dump(mode="json")
        expected_codes = set(sample.get("expected_context_codes", []))
        actual_codes = set(_active_context_codes(context_dict))
        context_recall, context_precision = _set_metrics(expected_codes, actual_codes)
        expected_features = set(sample.get("expected_active_features", []))
        actual_features = set(_active_numeric_features(diagnosis.features))
        audit_actual = actual_features & (FEATURE_BASE_UNIVERSE | expected_features | {
            name for name in diagnosis.features if name.endswith("_present")
        })
        feature_recall, feature_precision = _set_metrics(expected_features, audit_actual)
        actual_amounts = [float(event.amount_krw) for event in diagnosis.events if event.amount_krw is not None]
        amount_recall, amount_precision, amount_exact = _amount_metrics(sample.get("amounts_krw", []), actual_amounts)
        expected_roles = {code for code in expected_codes if code.startswith("ROLE_")}
        actual_roles = {code for code in actual_codes if code.startswith("ROLE_")}
        entity_recall, entity_precision = _set_metrics(expected_roles, actual_roles)
        brief_eval = _brief_metrics(sample, diagnosis.context.model_dump(mode="json"))
        normal_message = "현재 모델 판정 기준 미만입니다. 안전 확정을 의미하지 않으므로 의심 상황은 공식 채널로 확인하세요."
        initial_brief = diagnosis.context.summary if diagnosis.risk_level.value == "HIGH" else normal_message
        return {
            "sample_id": sample["sample_id"], "category": sample["category"], "status": "OK",
            "source": sample.get("source"), "transcript": sample["transcript"],
            "ground_truth": {key: value for key, value in sample.items() if key not in {"sample_id", "category", "source", "transcript"}},
            "A_extractor_candidate_features": {key: float(value) for key, value in diagnosis.features.items()},
            "A_active_feature_count": len(actual_features), "A_active_features": sorted(actual_features),
            "B_ml_selected_features": selected,
            "B_ml_selected_feature_count": len(selected),
            "B_ml_selected_zero_count": sum(value == 0 for value in selected.values()),
            "C_llm_payload": payload,
            "C_context_schema_field_count": len(context_dict),
            "C_active_context_code_count": len(actual_codes),
            "C_active_context_codes": sorted(actual_codes),
            "D_context_result": diagnosis.context.model_dump(mode="json"),
            "E_risk": {
                "risk_level": diagnosis.risk_level.value, "risk_score": diagnosis.risk_score,
                "model_label": diagnosis.model_label, "confidence": diagnosis.confidence,
                "partial_failure": diagnosis.partial_failure, "warnings": diagnosis.warnings,
                "model_metadata": diagnosis.model_metadata,
            },
            "F_generated_case_brief": diagnosis.context.summary,
            "F_general_api_initial_brief": initial_brief,
            "F_initial_report": initial_report.model_dump(mode="json"),
            "F_storage_projection": safe.model_dump(mode="json"),
            "F_storage_boundary": {"database_write_performed": False, "input_text": "", "reason": "validation safety"},
            "G_metrics": {
                "context_feature_recall": context_recall, "context_feature_precision": context_precision,
                "numeric_feature_recall": feature_recall, "numeric_feature_precision": feature_precision,
                "amount_recall": amount_recall, "amount_precision": amount_precision,
                "amount_exact_match": amount_exact, "entity_recall": entity_recall,
                "entity_precision": entity_precision, **brief_eval,
            },
            "runtime_seconds": (datetime.now(timezone.utc) - started).total_seconds(),
        }
    except Exception as exc:
        return {
            "sample_id": sample["sample_id"], "category": sample["category"], "status": "ERROR",
            "source": sample.get("source"), "transcript": sample["transcript"],
            "error_type": type(exc).__name__, "error": str(exc),
            "traceback": traceback.format_exc(),
            "runtime_seconds": (datetime.now(timezone.utc) - started).total_seconds(),
        }


async def analyze_samples(samples: list[dict[str, Any]], concurrency: int = 2) -> list[dict[str, Any]]:
    semaphore = asyncio.Semaphore(concurrency)

    async def guarded(sample: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            return await _analyze_one(DiagnosisService(), sample)

    return await asyncio.gather(*(guarded(sample) for sample in samples))


def add_semantic_similarity(records: list[dict[str, Any]]) -> str:
    valid = [record for record in records if record.get("status") == "OK"]
    if not valid:
        return "unavailable:no-successful-records"
    try:
        from openai import OpenAI

        texts: list[str] = []
        for record in valid:
            texts.extend([record["ground_truth"]["reference_brief"], record["F_generated_case_brief"]])
        model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        response = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=60, max_retries=1).embeddings.create(
            model=model, input=texts,
        )
        vectors = [np.asarray(item.embedding, dtype=float) for item in response.data]
        for index, record in enumerate(valid):
            left, right = vectors[index * 2], vectors[index * 2 + 1]
            similarity = float(np.dot(left, right) / (np.linalg.norm(left) * np.linalg.norm(right)))
            record["G_metrics"]["semantic_similarity"] = similarity
            record["G_metrics"]["embedding_model"] = model
        return model
    except Exception as exc:
        for record in valid:
            record["G_metrics"]["semantic_similarity"] = None
            record["G_metrics"]["embedding_model"] = None
        return f"unavailable:{type(exc).__name__}:{exc}"


def flatten_records(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for record in records:
        row = {
            "sample_id": record["sample_id"], "category": record["category"],
            "status": record["status"], "runtime_seconds": record.get("runtime_seconds"),
        }
        if record["status"] == "OK":
            metrics = record["G_metrics"]
            row.update({
                "risk_level": record["E_risk"]["risk_level"], "risk_score": record["E_risk"]["risk_score"],
                "model_label": record["E_risk"]["model_label"],
                "active_extractor_features": record["A_active_feature_count"],
                "ml_selected_features": record["B_ml_selected_feature_count"],
                "ml_zero_features": record["B_ml_selected_zero_count"],
                "llm_context_schema_fields": record["C_context_schema_field_count"],
                "active_context_codes": record["C_active_context_code_count"],
                "generated_case_brief": record["F_generated_case_brief"],
                "reference_brief": record["ground_truth"]["reference_brief"],
                **{key: value for key, value in metrics.items() if not isinstance(value, (list, dict))},
                "missing_critical_facts": " | ".join(metrics["critical_facts_missing"]),
                "contradicted_forbidden_facts": " | ".join(metrics["contradicted_forbidden_facts"]),
                "hallucinated_context_codes": " | ".join(metrics["hallucinated_context_codes"]),
                "unsupported_amounts_krw": " | ".join(map(str, metrics["unsupported_amounts_krw"])),
            })
        else:
            row.update({"error_type": record.get("error_type"), "error": record.get("error")})
        rows.append(row)
    return pd.DataFrame(rows)


def _mean(frame: pd.DataFrame, column: str) -> float:
    values = pd.to_numeric(frame.get(column), errors="coerce")
    return float(values.mean()) if values.notna().any() else float("nan")


def build_figures(frame: pd.DataFrame) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    ok = frame[frame["status"] == "OK"].copy()
    paths = []

    def save(name: str) -> None:
        path = FIGURE_DIR / name
        plt.tight_layout()
        plt.savefig(path, dpi=160, bbox_inches="tight")
        plt.close()
        paths.append(str(path.relative_to(ROOT)))

    plt.figure(figsize=(12, 4)); plt.bar(ok["sample_id"], ok["context_feature_recall"], color="#2878b5")
    plt.ylim(0, 1.05); plt.title("샘플별 Context Feature Recall"); plt.ylabel("Recall"); save("01_feature_recall_by_sample.png")

    category = ok.groupby("category", as_index=False)["context_feature_recall"].mean().sort_values("context_feature_recall")
    plt.figure(figsize=(9, max(5, len(category) * .28))); plt.barh(category["category"], category["context_feature_recall"], color="#54a24b")
    plt.xlim(0, 1.05); plt.title("카테고리별 Context Feature Recall"); save("02_feature_recall_by_category.png")

    missed = Counter()
    for value in ok["missing_critical_facts"].fillna(""):
        missed.update(item for item in value.split(" | ") if item)
    labels, values = zip(*missed.most_common(12)) if missed else (["누락 없음"], [0])
    plt.figure(figsize=(10, 5)); plt.barh(list(labels)[::-1], list(values)[::-1], color="#e45756")
    plt.title("자주 누락된 핵심 사실"); plt.xlabel("누락 샘플 수"); save("03_frequently_missing_facts.png")

    x = np.arange(len(ok)); width = .38
    plt.figure(figsize=(12, 4)); plt.bar(x - width/2, ok["critical_fact_recall"], width, label="핵심 사실 Recall")
    plt.bar(x + width/2, ok["fact_precision"], width, label="사실 Precision")
    plt.xticks(x, ok["sample_id"]); plt.ylim(0, 1.05); plt.legend(); plt.title("Context/Brief 보존 비교"); save("04_context_vs_brief.png")

    pivot = ok.pivot_table(index="category", values="hallucination_count", aggfunc="mean").sort_values("hallucination_count")
    plt.figure(figsize=(9, max(5, len(pivot) * .28))); plt.barh(pivot.index, pivot["hallucination_count"], color="#f2cf5b")
    plt.title("카테고리별 Hallucination 평균"); save("05_hallucination_by_category.png")

    metric_cols = ["context_feature_recall", "context_feature_precision", "critical_fact_recall", "fact_precision", "semantic_similarity"]
    heat = ok.set_index("sample_id")[[col for col in metric_cols if col in ok]].apply(pd.to_numeric, errors="coerce")
    plt.figure(figsize=(8, max(5, len(heat) * .22))); plt.imshow(heat.fillna(0), aspect="auto", cmap="RdYlGn", vmin=0, vmax=1)
    plt.colorbar(label="score"); plt.xticks(range(len(heat.columns)), heat.columns, rotation=30, ha="right")
    plt.yticks(range(len(heat.index)), heat.index); plt.title("샘플 × 평가 지표 Heatmap"); save("06_metric_heatmap.png")

    flow_values = [152, 23, 12, int(round(ok["active_context_codes"].mean())) if len(ok) else 0]
    plt.figure(figsize=(8, 4)); plt.bar(["Extractor 후보", "ML selected", "LLM schema", "LLM active 평균"], flow_values, color=["#4c78a8", "#72b7b2", "#f58518", "#e45756"])
    plt.title("Feature 흐름별 개수"); plt.ylabel("개수"); save("07_feature_flow_counts.png")
    return paths


def write_inventory_docs(inventory: pd.DataFrame) -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    inventory.to_csv(RESULT_DIR / "context_feature_inventory.csv", index=False, encoding="utf-8-sig")
    inventory.to_csv(DOCS_DIR / "context_feature_inventory_ko.csv", index=False, encoding="utf-8-sig")
    llm = inventory[inventory["LLM 입력 여부"] == "O"]
    internal = inventory[inventory["LLM 입력 여부"] == "X"]
    category_rows = []
    for code, label in CONTEXT_CODE_LABELS.items():
        category_rows.append({"PPT 카테고리": _context_group(code), "실제 코드": code, "한국어 의미": label})
    category_frame = pd.DataFrame(category_rows)
    text = f"""# Context Feature Inventory (Runtime 기준)

생성일: {datetime.now(timezone.utc).astimezone().isoformat()}

## Runtime에서 확인한 세 계층

| 계층 | 실제 개수 | Runtime 전달 규칙 |
| --- | ---: | --- |
| A. Window Feature Extractor 전체 후보 | {len(features_from_events([]))} | 모든 후보가 숫자 dict로 계산됨 |
| B. ML 모델 selected Feature | {len(load_model_bundle()['model_features'])} | 23개 열을 고정 순서로 구성하며 0도 전달 |
| C. `case_context_features` LLM Context 필드 | {len(CONTEXT_FIELDS)} | 12개 필드를 모두 JSON 직렬화; 코드 목록은 active만 포함 |
| C-보조. `signals[]` 이벤트 속성 | {len(SIGNAL_FIELDS)} | 이벤트가 있을 때만 item 생성; 금액/요구 여부는 조건부 |

전체 LLM payload의 명명된 schema 슬롯은 top-level 4개 + `signals[]` 7개 + nested context 12개 = 23개입니다(컨테이너 포함). leaf 기준은 21개입니다. 152개 숫자 Feature 및 23개 ML selected 벡터는 LLM에 직접 전달되지 않습니다.

## A. LLM 자연어 맥락 생성에 실제 사용되는 핵심 Field

{llm[['대분류','실제 Feature/Field명','한국어 의미','값 형태','어떤 정보인가','LLM 입력 여부','자연어 생성 시 사용 예']].to_markdown(index=False)}

## B. 내부 Extractor/ML에는 존재하지만 LLM 자연어 생성에는 직접 사용되지 않는 Feature

전체 {len(internal)}개 행은 CSV에 수록했습니다. 아래는 ML selected 23개입니다.

{internal[internal['ML 입력 여부'] == 'O'][['대분류','실제 Feature/Field명','한국어 의미','값 형태','어떤 정보인가','LLM 입력 여부','자연어 생성 시 사용 예']].to_markdown(index=False)}

## PPT용 한국어 카테고리

{category_frame.to_markdown(index=False)}

## 연결 관계

`DiagnosisService.analyze()`는 원문을 Window 이벤트/ML 경로와 독립 Context Extractor 경로에 각각 일시적으로 전달합니다. 이후 `signal_context_payload(events)`에 독립 `case_context_features`를 덮어써서 Context LLM에 보냅니다. Context LLM의 `ContextResult.summary`가 HIGH Case에서 `initial_brief`가 되며, `InitialReportBuilder`의 summary 섹션에도 같은 값이 들어갑니다. Shared Case 저장 직전 `project_diagnosis_for_case()`가 원문 evidence/window text를 안전 라벨로 치환하고 `input_text`는 빈 문자열로 저장합니다.
"""
    (DOCS_DIR / "context_feature_inventory_ko.md").write_text(text, encoding="utf-8")


def write_summary(records: list[dict[str, Any]], frame: pd.DataFrame, embedding_backend: str, figures: list[str]) -> None:
    ok = frame[frame["status"] == "OK"]
    errors = frame[frame["status"] != "OK"]
    priority = [
        ("Contradiction", int(pd.to_numeric(ok.get("contradiction_count"), errors="coerce").fillna(0).sum()) if len(ok) else 0, "금지 사실이 Brief에 나타난 건수"),
        ("Critical Fact Recall", _mean(ok, "critical_fact_recall"), "높을수록 좋음"),
        ("Hallucination", int(pd.to_numeric(ok.get("hallucination_count"), errors="coerce").fillna(0).sum()) if len(ok) else 0, "비근거 코드·금액 건수"),
        ("Feature Extraction", _mean(ok, "context_feature_recall"), "Context code recall"),
        ("Semantic Similarity", _mean(ok, "semantic_similarity"), "참조 Brief와 embedding cosine"),
    ]
    selected_examples = []
    category_names = sorted(frame["category"].dropna().unique())
    missing_counter: Counter[str] = Counter()
    for record in records:
        if record.get("status") == "OK":
            missing_counter.update(record["G_metrics"]["critical_facts_missing"])
    top_missing = missing_counter.most_common(10)
    normal_ids = {
        record["sample_id"] for record in records
        if any(code.startswith("NORMAL_") for code in record.get("ground_truth", {}).get("expected_context_codes", []))
    }
    high_ids = set(ok.loc[ok["risk_level"] == "HIGH", "sample_id"])
    normal_false_positives = sorted(normal_ids & high_ids)
    suspicious_ids = set(ok["sample_id"]) - normal_ids
    suspicious_below_threshold = sorted(suspicious_ids - high_ids)
    first_ok = next((record for record in records if record.get("status") == "OK"), None)
    if len(ok):
        candidates = pd.concat([
            ok.nsmallest(min(3, len(ok)), "critical_fact_recall"),
            ok.nlargest(min(2, len(ok)), "critical_fact_recall"),
        ]).drop_duplicates("sample_id").head(5)
        for sample_id in candidates["sample_id"]:
            record = next(item for item in records if item["sample_id"] == sample_id)
            selected_examples.append(
                f"### {sample_id} — {record['category']}\n\n"
                f"- 원문: {record['transcript'].replace(chr(10), ' / ')}\n"
                f"- Ground Truth: {', '.join(record['ground_truth']['critical_facts'])}\n"
                f"- 구조화 Context: {', '.join(record['C_active_context_codes']) or '없음'}\n"
                f"- 생성 Brief: {record['F_generated_case_brief']}\n"
                f"- 누락: {', '.join(record['G_metrics']['critical_facts_missing']) or '없음'}\n"
                f"- 모순: {', '.join(record['G_metrics']['contradicted_forbidden_facts']) or '없음'}\n"
            )
    priority_table = "\n".join(f"| {name} | {value:.4f} | {note} |" if isinstance(value, float) else f"| {name} | {value} | {note} |" for name, value, note in priority)
    summary = f"""# Context Reconstruction Validation Summary

실행 시각: {datetime.now(timezone.utc).astimezone().isoformat()}

## 실행 범위

- 총 샘플: {len(frame)}개 (성공 {len(ok)} / 실패 {len(errors)})
- 운영 코드: `DiagnosisService.analyze` → `WindowAiAdapter`/독립 Context Extractor → 실제 model pkl → Context LLM
- DB 기록: 수행하지 않음. 운영 `project_diagnosis_for_case`와 `InitialReportBuilder`까지 실행해 저장 직전 구조를 검증함.
- Embedding: `{embedding_backend}`
- 검증 카테고리: {', '.join(category_names)}

## 핵심 Runtime 수치

- Extractor 후보 Feature: **{len(features_from_events([]))}개**
- ML selected Feature: **{len(load_model_bundle()['model_features'])}개** (0값도 모두 모델 DataFrame에 전달)
- LLM `case_context_features` schema: **{len(CONTEXT_FIELDS)}개 필드** (빈 목록 포함 직렬화)
- LLM에 전달되는 숫자 Feature/ML 벡터: **0개**
- LLM 전체 payload 경로 슬롯: **23개(컨테이너 포함), leaf 21개**
- 샘플당 active Context code 평균: **{_mean(ok, 'active_context_codes'):.2f}개**
- 실제 예시 `{first_ok['sample_id'] if first_ok else '-'}`: active 숫자 Feature **{first_ok['A_active_feature_count'] if first_ok else '-'}개**, active Context code **{first_ok['C_active_context_code_count'] if first_ok else '-'}개**, ML selected 23개 중 0값 **{first_ok['B_ml_selected_zero_count'] if first_ok else '-'}개**

## 최종 우선순위 평가

| 우선순위 | 결과 | 해석 |
| --- | ---: | --- |
{priority_table}

## 전체 지표

| 지표 | 평균 |
| --- | ---: |
| Context Feature Recall | {_mean(ok, 'context_feature_recall'):.4f} |
| Context Feature Precision | {_mean(ok, 'context_feature_precision'):.4f} |
| Numeric Feature Recall | {_mean(ok, 'numeric_feature_recall'):.4f} |
| Numeric Feature Precision | {_mean(ok, 'numeric_feature_precision'):.4f} |
| Entity Recall | {_mean(ok, 'entity_recall'):.4f} |
| Amount Recall | {_mean(ok, 'amount_recall'):.4f} |
| Critical Fact Recall | {_mean(ok, 'critical_fact_recall'):.4f} |
| Fact Precision | {_mean(ok, 'fact_precision'):.4f} |
| Semantic Similarity | {_mean(ok, 'semantic_similarity'):.4f} |

## 가장 크게 누락된 정보

{pd.DataFrame(top_missing, columns=['누락 핵심 사실','샘플 수']).to_markdown(index=False) if top_missing else '누락 없음'}

## Risk 경계 오류

- 정상 Ground Truth {len(normal_ids)}건 중 HIGH 판정: **{len(normal_false_positives)}건** ({', '.join(normal_false_positives) or '없음'})
- 위험 Ground Truth {len(suspicious_ids)}건 중 HIGH 미달: **{len(suspicious_below_threshold)}건** ({', '.join(suspicious_below_threshold) or '없음'})

## 샘플별 결과

{ok[['sample_id','category','risk_level','risk_score','context_feature_recall','critical_fact_recall','fact_precision','hallucination_count','contradiction_count','amount_preservation','semantic_similarity']].to_markdown(index=False) if len(ok) else '성공 샘플 없음'}

## 대표 샘플 5건 상세 비교

{''.join(selected_examples)}

## 오류 샘플

{errors[['sample_id','category','error_type','error']].to_markdown(index=False) if len(errors) else '없음'}

## 그래프

{chr(10).join(f'- `{path}`' for path in figures)}

## 평가 해석상 주의

- Feature precision/recall은 Ground Truth에 명시한 핵심 active 신호와 실제 representative-window active 신호를 비교합니다. 파생 count·QC·interaction Feature는 inventory에는 포함하지만 이 점수의 분모에서는 제외합니다.
- Brief 핵심 사실/모순/Hallucination은 고정된 한국어 키워드·금액 규칙 기반 감사입니다. LLM judge를 추가로 호출하지 않아 재현 가능하지만, 완전한 의미 판정은 아닙니다.
- Semantic similarity는 의미적 유사성만 보며 사실 정확성을 보장하지 않습니다. 따라서 최종 우선순위에서 가장 낮게 둡니다.
- 독립 Context Extractor의 33개 code vocabulary 중 active 관찰만 배열에 담기며, 비활성 code를 0으로 보내지는 않습니다. 반대로 12개 필드 자체와 기본 빈 배열은 모두 LLM payload에 포함됩니다.
- 호출 결과는 LLM 비결정성의 영향을 받을 수 있으며, 본 결과는 위 실행 시각의 단일 run입니다.

## PPT에 바로 사용할 수 있는 결론

| 질문 | Runtime 검증 결론 |
| --- | --- |
| Feature Extractor는 무엇을 만드는가? | Window별 숫자 후보 152개를 계산합니다. |
| ML은 무엇을 받는가? | 고정 순서 23개 selected Feature를 받으며, 값이 0이어도 열에서 제거하지 않습니다. |
| LLM은 숫자 Feature를 받는가? | 받지 않습니다. 숫자 152개/selected 23개 중 LLM 직접 입력은 0개입니다. |
| LLM이 받는 Context는 몇 개인가? | `case_context_features` 12개 필드입니다. 전체 요청 schema는 top-level 4 + signal 속성 7 + nested 12 = 23개 슬롯입니다. |
| 비활성 Feature는 전달되는가? | Context code는 active 관찰만 배열에 포함합니다. 다만 빈 배열을 포함한 12개 필드 자체는 모두 전달됩니다. |
| initial_brief 연결은? | HIGH Case에서 `ContextResult.summary`가 그대로 `initial_brief`와 초기 리포트 summary가 됩니다. NORMAL은 Case를 만들지 않고 고정 안내문을 반환합니다. |
| Shared Case에는 원문이 남는가? | `input_text`는 빈 문자열이며, event evidence와 window text는 저장 전 안전 라벨로 치환됩니다. |
| 현재 품질 결론 | Context Feature Recall {_mean(ok, 'context_feature_recall'):.3f}, 핵심 사실 Recall {_mean(ok, 'critical_fact_recall'):.3f}로 PPT에서 “완성”보다 “구조는 구현됐으나 재구성 품질 개선 필요”로 표현해야 합니다. |

## 코드 개선 제안 (본 작업에서는 미적용)

1. Event/Context instruction의 정상·부인·완료 상태 구분을 강화하고 prompt 회귀 테스트를 추가합니다.
2. 독립 Context Extractor가 `PURPOSE_`, `DEADLINE_`, `CUSTOMER_`, `NORMAL_`을 direct 배열에서 버리지 않도록 명시 필드를 추가하거나 `observations` 소비를 강제합니다.
3. `amount_values_krw`가 현재 독립 추출 경로에서 항상 빈 배열인 단절을 해소하고, event 금액과 요구 금액을 구분해 Context LLM에 전달합니다.
4. `DENIED`/`REPORTED`/`REQUESTED` 상태를 Brief 템플릿의 필수 문장으로 만들어 “요구”와 “이미 수행”의 혼동을 막습니다.
5. 정상 상담 hard-negative와 개인정보·현금전달·단일 인증번호 사례를 모델 재학습/threshold calibration 세트에 포함합니다.
6. 핵심 사실은 자유 생성 summary에만 맡기지 말고 구조화 관찰에서 결정적으로 렌더링한 뒤 LLM이 문장만 다듬도록 합니다.
7. 본 30개 세트를 CI의 외부-LLM 비정기 eval과 고정 fixture 기반 회귀 테스트로 분리해 운영합니다.
"""
    (RESULT_DIR / "context_reconstruction_summary.md").write_text(summary, encoding="utf-8")


def run(force: bool = False, limit: int | None = None, concurrency: int = 2) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    samples = json.loads(SAMPLES_PATH.read_text(encoding="utf-8"))
    if limit:
        samples = samples[:limit]
    write_inventory_docs(build_inventory())
    json_path = RESULT_DIR / "context_reconstruction_results.json"
    if json_path.exists() and not force:
        records = json.loads(json_path.read_text(encoding="utf-8"))
    else:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is required for the actual production runtime validation.")
        records = asyncio.run(analyze_samples(samples, concurrency=concurrency))
        embedding_backend = add_semantic_similarity(records)
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "runtime": "MVP_v3 production imports; no database write",
            "embedding_backend": embedding_backend,
            "records": records,
        }
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if isinstance(records, dict):
        embedding_backend = records.get("embedding_backend", "unknown")
        records = records["records"]
    else:
        embedding_backend = next((item.get("G_metrics", {}).get("embedding_model") for item in records if item.get("status") == "OK"), "unknown")
    frame = flatten_records(records)
    frame.to_csv(RESULT_DIR / "context_reconstruction_results.csv", index=False, encoding="utf-8-sig")
    figures = build_figures(frame)
    write_summary(records, frame, str(embedding_backend), figures)
    return frame, records


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--concurrency", type=int, default=2)
    args = parser.parse_args()
    output, _ = run(force=args.force, limit=args.limit, concurrency=args.concurrency)
    print(output.to_string(index=False))
