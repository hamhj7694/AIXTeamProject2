"""Q01~Q08의 실제 문서 질문으로 SimpleRetriever를 확인하는 실행 스크립트."""

from __future__ import annotations

import re
from pathlib import Path

try:
    from .simple_retriever import RAG_DIRECTORY, SimpleRetriever
except ImportError:  # python ai_system_design/rag/retrieval/test_queries.py 실행 지원
    from simple_retriever import RAG_DIRECTORY, SimpleRetriever


QUESTIONS_PATH = RAG_DIRECTORY / "02_mvp_rag_questions.md"
RESULT_PATH = Path(__file__).resolve().with_name("mvp_retrieval_result.md")
EXPECTED_KNOWLEDGE_IDS = {
    "Q01": {"VER-001", "VER-002"},
    "Q02": {"VER-001", "VER-002"},
    "Q03": {"REC-001"},
    "Q04": {"REP-001", "REP-002"},
    "Q05": {"REC-001", "REC-002"},
    "Q06": {"VER-002", "SEC-001"},
    "Q07": {"SEC-002"},
    "Q08": {"REP-001", "REP-002"},
}


def load_representative_questions() -> dict[str, str]:
    """문서의 Q01~Q08 제목을 검색 Query로 직접 읽는다."""
    content = QUESTIONS_PATH.read_text(encoding="utf-8")
    matches = re.findall(r"^### (Q0[1-8])\. (.+)$", content, flags=re.MULTILINE)
    questions = dict(matches)
    if set(questions) != set(EXPECTED_KNOWLEDGE_IDS):
        raise ValueError("Q01~Q08 headings were not found in 02_mvp_rag_questions.md")
    return questions


def evaluate() -> list[dict[str, object]]:
    retriever = SimpleRetriever()
    evaluations: list[dict[str, object]] = []
    for question_id, query in load_representative_questions().items():
        results = retriever.search(query, top_k=3)
        actual_ids = [result["knowledge_id"] for result in results]
        expected_ids = EXPECTED_KNOWLEDGE_IDS[question_id]
        passed = bool(expected_ids.intersection(actual_ids))
        evaluations.append(
            {
                "question_id": question_id,
                "query": query,
                "expected_ids": sorted(expected_ids),
                "actual_ids": actual_ids,
                "passed": passed,
            }
        )
    return evaluations


def write_result_markdown(evaluations: list[dict[str, object]]) -> None:
    passed_count = sum(bool(item["passed"]) for item in evaluations)
    failed_ids = [str(item["question_id"]) for item in evaluations if not item["passed"]]
    lines = [
        "# MVP Retrieval 결과",
        "",
        "| Question | Expected | Top-3 | Result |",
        "|---|---|---|---|",
    ]
    for item in evaluations:
        lines.append(
            "| {question_id} | {expected} | {actual} | {result} |".format(
                question_id=item["question_id"],
                expected=", ".join(item["expected_ids"]),
                actual=", ".join(item["actual_ids"]) or "검색 결과 없음",
                result="PASS" if item["passed"] else "FAIL",
            )
        )
    lines.extend(
        [
            "",
            f"- PASS: {passed_count}/{len(evaluations)}",
            f"- FAIL: {', '.join(failed_ids) if failed_ids else '없음'}",
            "- 이 결과는 검색 적합성만 확인한다. Q02·Q03의 PARTIAL Coverage를 완전한 답변으로 해석하지 않는다.",
        ]
    )
    RESULT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    evaluations = evaluate()
    write_result_markdown(evaluations)
    for item in evaluations:
        print(
            f"{item['question_id']}: {'PASS' if item['passed'] else 'FAIL'} "
            f"Top-3={', '.join(item['actual_ids']) or '검색 결과 없음'}"
        )
    return 0 if all(item["passed"] for item in evaluations) else 1


if __name__ == "__main__":
    raise SystemExit(main())
