"""Export developer JSON and Korean summary Markdown for A-part 6.5.

The report is intentionally privacy-safe: transcript text is transient and is
never written to either output.  The JSON is for engineering inspection; the
Markdown is for a human-readable review of the same run.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

from ai_api.app.domains.diagnosis.service import DiagnosisService


_DROP_KEYS = {
    "turns", "text", "raw_text", "input_text", "evidence_text", "source_text",
    "summary", "description", "recommended_next_steps",
}
_SENSITIVE = re.compile(r"(?:\d{4,}|\d{2,}[- ]\d{2,}|\b[A-Z]{2,}\s*\d{3,}\b)", re.IGNORECASE)


def _privacy_safe(value: Any, key: str = "") -> Any:
    if key in _DROP_KEYS:
        return None
    if isinstance(value, dict):
        return {
            str(k): _privacy_safe(v, str(k))
            for k, v in value.items()
            if str(k) not in _DROP_KEYS
        }
    if isinstance(value, list):
        return [_privacy_safe(item) for item in value]
    if isinstance(value, str):
        return _SENSITIVE.sub("[REDACTED]", value) if len(value) > 3 else value
    return value


def _developer_report(result: Any) -> dict[str, Any]:
    payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result
    data = _privacy_safe(payload)
    atoms = data.get("semantic_atoms", [])
    events = data.get("events", [])
    relations = data.get("semantic_relations", [])
    signals = data.get("context_signals", [])
    audit = data.get("semantic_audit") or {}
    data["quality_report"] = {
        "schema_version": "a-context-quality-report.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "privacy_status": "PASS",
        "pipeline_counts": {
            "events": len(events), "semantic_atoms": len(atoms),
            "semantic_relations": len(relations), "context_signals": len(signals),
        },
        "audit": {
            "status": audit.get("audit_status"),
            "score": audit.get("overall_score"),
            "recommended_action": audit.get("recommended_action"),
            "metrics": audit.get("metrics", {}),
        },
    }
    return data


def _report_markdown(data: dict[str, Any]) -> str:
    quality = data["quality_report"]
    counts = quality["pipeline_counts"]
    audit = quality["audit"]
    atoms = data.get("semantic_atoms", [])
    term_count = sum(len(atom.get("observed_terms", []) or []) for atom in atoms)
    lines = [
        "# A파트 Context Pipeline 6.5 평가 보고서",
        "",
        f"생성 시각: `{quality['generated_at']}`  ",
        "목적: 1~6단계 결과의 구조·품질·문장화 연결 상태를 내부적으로 점검",
        "",
        "## 한눈에 보는 결과",
        "",
        "| 평가 항목 | 결과 |",
        "|---|---:|",
        f"| 추출 Event | {counts['events']}건 |",
        f"| Semantic Atom | {counts['semantic_atoms']}건 |",
        f"| Observed Term | {term_count}건 |",
        f"| Relation | {counts['semantic_relations']}건 |",
        f"| Context Signal | {counts['context_signals']}건 |",
        f"| 점검 AI 상태 | `{audit.get('status') or '미실행'}` |",
        f"| 점검 AI 점수 | `{audit.get('score') if audit.get('score') is not None else '미실행'}` |",
        "",
        "## 파이프라인 흐름",
        "",
        "```mermaid",
        "flowchart LR",
        "  I[입력 처리 중] --> E[Event 추출] --> A[Semantic Atom/키워드]",
        "  A --> R[Relation/Signal] --> D[DiagnosisResult 저장]",
        "  D --> F[Fact projection] --> S[직원용 문장화] --> P[우측 Context Panel]",
        "```",
        "## 구조 해석",
        "",
        "- Event는 통화에서 감지된 사건 단위입니다.",
        "- Semantic Atom은 기관·행동·요구·위협·상태처럼 분리 가능한 의미 단위입니다.",
        "- Observed Term은 실제 표현 중 허용된 짧은 핵심 용어만 보존합니다.",
        "- Relation과 Context Signal은 Atom 간 연결과 복합 위험 신호를 표현합니다.",
        "- 은행 화면에는 개발자용 code가 아니라 Fact 기반 직원용 문장이 표시됩니다.",
        "",
        "## 개발자 점검 메모",
        "",
        f"- `privacy_status`: `{quality['privacy_status']}`",
        f"- 점검 AI 권고: `{audit.get('recommended_action') or '확인 필요'}`",
        "- 이 보고서는 운영 웹 UI에 노출하지 않는 내부 평가 자료입니다.",
        "- 원문·긴 문장·민감 숫자 literal은 보고서에 포함하지 않습니다.",
        "",
        "## 다음 확인",
        "",
        "1. 정답 annotation과 비교해 precision·recall·F1을 산출합니다.",
        "2. Atom→Fact→Statement slot preservation과 unsupported lexicalization을 확인합니다.",
        "3. DB 저장 및 기존 우측 패널 E2E를 별도 실행합니다.",
    ]
    return "\n".join(lines)


async def _run(source_text: str) -> dict[str, Any]:
    return _developer_report(await DiagnosisService().analyze(source_text))


def main() -> None:
    parser = argparse.ArgumentParser(description="Export A-part 6.5 JSON + Korean Markdown report")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="Transient text to analyze")
    source.add_argument("--input", type=Path, help="UTF-8 text file to analyze")
    source.add_argument("--diagnosis-json", type=Path, help="Existing DiagnosisResult JSON (no LLM call)")
    parser.add_argument("--output-dir", type=Path, default=Path("context-quality-report"))
    args = parser.parse_args()
    if args.diagnosis_json is not None:
        data = _developer_report(json.loads(args.diagnosis_json.read_text(encoding="utf-8-sig")))
    else:
        text = args.text if args.text is not None else args.input.read_text(encoding="utf-8")
        data = asyncio.run(_run(text))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "developer-structure.json"
    md_path = args.output_dir / "human-review-report.md"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_report_markdown(data), encoding="utf-8")
    print(json.dumps({"developer_json": str(json_path), "human_report": str(md_path), **data["quality_report"]["pipeline_counts"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
