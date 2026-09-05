"""Case-local lexical RAG. No remote embedding calls, persistent copies or writes.

TF-IDF character n-grams support Korean spacing differences; a small synonym
map is not a semantic embedding model. Structured facts always outrank retrieval.
Only already-authorized records enter the index. Cache keys include case, audience
and the actual content fingerprint, so edits/deletions cannot leave stale results.
"""
from __future__ import annotations

import hashlib
import math
import re
from collections import Counter, OrderedDict
from dataclasses import dataclass

from contracts.user_text import user_text


@dataclass(frozen=True)
class CaseRecord:
    case_id: str
    source_id: str
    kind: str
    text: str
    audience: str = "BANK_INTERNAL"


def normalized_text(text: str) -> str:
    text = re.sub(r"\s+", "", user_text(text).casefold())
    for before, after in (
        ("이체", "송금"), ("돈을보내", "송금"), ("돈을보냈", "송금했"),
        ("계좌로보냈", "송금했"), ("패스워드", "비밀번호"),
        ("원격조종", "원격제어"), ("수사기관", "검찰"),
    ):
        text = text.replace(before, after)
    return re.sub(r"[^가-힣a-z0-9]", "", text)


def _terms(text: str) -> Counter:
    value = normalized_text(text)
    return Counter(value[i:i + n] for n in (2, 3) for i in range(max(0, len(value) - n + 1)))


def similar_question(candidate: str, previous: str) -> bool:
    """Conservative lexical duplicate check, never a fact-confirmation signal."""
    left, right = normalized_text(candidate), normalized_text(previous)
    if min(len(left), len(right)) < 8:
        return False
    if left == right:
        return True
    a, b = set(_terms(left)), set(_terms(right))
    return bool(a and b) and 2 * len(a & b) / (len(a) + len(b)) >= 0.88


class CaseRetriever:
    def __init__(self, max_indexes: int = 32):
        self.max_indexes = max_indexes
        self._indexes: OrderedDict = OrderedDict()

    def search(self, case_id: str, audience: str, query: str, records: list[CaseRecord], *, limit: int = 6) -> list[dict]:
        # Filter BEFORE statistics/indexing. Even IDF must not use another case.
        allowed = [r for r in records if r.case_id == case_id and (
            r.audience == "CUSTOMER" or (audience == "BANK_INTERNAL" and r.audience == "BANK_INTERNAL")
        )][-2000:]
        fingerprint = hashlib.sha256(repr(allowed).encode()).hexdigest()
        key = (case_id, audience)
        cached = self._indexes.get(key)
        if cached is None or cached[0] != fingerprint:
            counts = [_terms(r.text[:750]) for r in allowed]
            df = Counter(term for row in counts for term in row)
            idf = {term: math.log((len(counts) + 1) / (freq + 1)) + 1 for term, freq in df.items()}
            vectors = []
            for row in counts:
                vector = {term: (1 + math.log(freq)) * idf[term] for term, freq in row.items()}
                norm = math.sqrt(sum(v * v for v in vector.values())) or 1
                vectors.append({term: value / norm for term, value in vector.items()})
            cached = (fingerprint, allowed, idf, vectors)
            self._indexes[key] = cached
        self._indexes.move_to_end(key)
        while len(self._indexes) > self.max_indexes:
            self._indexes.popitem(last=False)
        _, documents, idf, vectors = cached
        query_vector = {term: (1 + math.log(freq)) * idf[term] for term, freq in _terms(query[:6000]).items() if term in idf}
        norm = math.sqrt(sum(v * v for v in query_vector.values())) or 1
        ranked = []
        for index, vector in enumerate(vectors):
            score = sum(value * vector.get(term, 0) for term, value in query_vector.items()) / norm
            if score >= 0.10:
                ranked.append((score, index))
        return [{"source_id": documents[i].source_id, "kind": documents[i].kind,
                 "text": documents[i].text[:750], "score": round(score, 4)}
                for score, i in sorted(ranked, reverse=True)[:max(0, min(limit, 6))]]


retriever = CaseRetriever()

# Explicit contract mapping only: never guess a fact's meaning from its label.
SEMANTIC_FIELDS = {
    "transfer.actual.status": "transfer_status",
    "transfer.purpose": "transfer_purpose",
    "exposure.personal_information": "personal_information_exposure",
    "exposure.authentication_information": "authentication_information_exposure",
    "device.remote_control_app": "remote_control_app",
    "offender.claimed_organization": "claimed_organization",
    "offender.incident_claim": "incident_claim",
}


def merge_support_records(resources, facts, actions):
    data = resources.model_dump(mode="json")
    new_facts = [{"fact_id": f["fact_id"], "field": SEMANTIC_FIELDS[f["semantic_key"]],
                  "value": f["display_value"], "status": f["status"]}
                 for f in data["facts"] if f["status"] in {"CONFIRMED", "PROPOSED"} and f["semantic_key"] in SEMANTIC_FIELDS]
    confirmed = {f["field"] for f in new_facts if f["status"] == "CONFIRMED"}
    from .repository import normalize_target_field
    merged_facts = [f for f in facts if normalize_target_field(str(f.get("field", ""))) not in confirmed] + new_facts
    tasks = [{"action_id": t["task_id"], "action_type": "STAFF_TASK",
              "status": t["status"], "note": f"{t['title']}: {t['description']}"}
             for t in data["tasks"]]
    return merged_facts, [*actions, *tasks]


_STATUS = {"CONFIRMED": "담당자 확인", "PROPOSED": "확인 전 진술", "TODO": "예정",
           "IN_PROGRESS": "진행 중", "BLOCKED": "보류", "COMPLETED": "담당자 완료 기록",
           "CANCELLED": "취소", "PENDING": "대기", "ASKED": "답변 대기", "ANSWERED": "답변 접수·사실 확정 아님"}


def workspace_records(case_id: str, resources) -> list[CaseRecord]:
    data = resources.model_dump(mode="json")
    if data["case_id"] != case_id:
        raise ValueError("Case context source mismatch")
    records = []
    for f in data["facts"]:
        if f["status"] in {"CONFIRMED", "PROPOSED"}:
            records.append(CaseRecord(case_id, f["fact_id"], "사실", user_text(
                f"{f['display_label']}: {f['display_value']} ({_STATUS[f['status']]})")))
    for t in data["tasks"]:
        records.append(CaseRecord(case_id, t["task_id"], "담당자 업무", user_text(
            f"{t['title']} ({_STATUS[t['status']]}): {t['description']} / 결과: {t.get('result_summary') or '등록 안 됨'} / 취소 사유: {t.get('cancellation_reason') or '없음'}")))
    superseded = {d["supersedes_decision_id"] for d in data["decisions"] if d.get("supersedes_decision_id")}
    for d in data["decisions"]:
        if d["decision_id"] not in superseded:
            records.append(CaseRecord(case_id, d["decision_id"], "담당자 결정", user_text(f"{d['title']}: {d['rationale']}")))
    return records


def collect_records(case_id: str, *, messages=(), questions=(), facts=(), verifications=(), staff=(), customer=False) -> list[CaseRecord]:
    result = [] if customer else list(staff)
    for m in messages:
        if not m.get("message_id") or m.get("case_id", case_id) != case_id:
            continue
        visibility = m.get("visibility")
        if visibility not in {"CUSTOMER", "BANK_INTERNAL"} or (customer and visibility != "CUSTOMER"):
            continue
        if m.get("message_kind") in {"AI_RESPONSE", "REPORT_CARD"} or m.get("actor_type") in {"BANK_AGENT", "CUSTOMER_AGENT"}:
            continue  # Previous generated statements are not evidence.
        result.append(CaseRecord(case_id, m["message_id"], "대화·작성자 진술", user_text(
            f"{m.get('actor_display_name', '상담 참여자')}: {m.get('content', '')}"), visibility))
    for q in questions:
        if not q.get("question_id") or q.get("case_id", case_id) != case_id:
            continue
        if customer and q.get("status") not in {"ASKED", "ANSWERED"}:
            continue
        text = f"질문: {q.get('question_text', '')} / 답변: {q.get('answer_text') or '아직 없음'} ({_STATUS.get(q.get('status'), '확인 필요')})"
        result.append(CaseRecord(case_id, q["question_id"], "질문·고객 답변", user_text(text), "CUSTOMER" if q.get("status") in {"ASKED", "ANSWERED"} else "BANK_INTERNAL"))
    if not customer:
        for f in facts:
            if f.get("case_id", case_id) == case_id and f.get("fact_id") and f.get("status") in {"PROPOSED", "CONFIRMED"}:
                result.append(CaseRecord(case_id, f["fact_id"], "기존 사실", user_text(f"{f.get('field')}: {f.get('value')} ({_STATUS[f['status']]})")))
    for v in verifications:
        if not v.get("verification_task_id") or v.get("case_id", case_id) != case_id:
            continue
        public = v.get("customer_visible") and v.get("status") == "COMPLETED" and v.get("result_summary")
        if customer and not public:
            continue
        text = f"{v.get('target')}: {v.get('result_summary') or v.get('claim', '')} ({_STATUS.get(v.get('status'), '확인 필요')})"
        result.append(CaseRecord(case_id, v["verification_task_id"], "기관 확인", user_text(text), "CUSTOMER" if public else "BANK_INTERNAL"))
    return result


def retrieve_context(case_id: str, prompt: str, records: list[CaseRecord], *, customer=False) -> list[str]:
    hits = retriever.search(case_id, "CUSTOMER" if customer else "BANK_INTERNAL", prompt, records)
    return [f"[출처: {h['kind']} / {h['source_id']}] {h['text']}" for h in hits]


def staff_context(records: list[CaseRecord]) -> list[str]:
    # Include current staff decisions even when they do not match query words.
    return [f"{r.kind}: {r.text[:350]}" for kind in ("사실", "담당자 업무", "담당자 결정")
            for r in [r for r in records if r.kind == kind][-6:]]
