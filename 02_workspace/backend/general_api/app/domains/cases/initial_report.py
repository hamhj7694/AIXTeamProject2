from __future__ import annotations

from datetime import datetime, timezone

from contracts.diagnosis import DiagnosisResult, InitialReport, ReportSection


class InitialReportBuilder:
    """최초 Diagnosis 결과를 LIVE Report의 안정적인 Section으로 투영한다."""

    def build(self, case_id: str, diagnosis: DiagnosisResult) -> InitialReport:
        amount = float(diagnosis.features.get("requested_amount_max", 0) or 0)
        transfer_requested = bool(diagnosis.features.get("money_transfer_present", 0))
        evidence = [item.model_dump(mode="json") for item in diagnosis.evidence]
        sections = [
            ReportSection(section_key="summary", content={
                "text": diagnosis.context.summary,
                "incident_type": diagnosis.context.incident_type,
                "confidence": diagnosis.context.confidence,
            }),
            ReportSection(section_key="risk_context", content={
                "risk_level": diagnosis.risk_level.value,
                "risk_score": diagnosis.risk_score,
                "model_label": diagnosis.model_label,
                "evidence": evidence,
                "model_status": diagnosis.model_metadata.get("model_status"),
            }),
            ReportSection(section_key="transfer_status", content={
                "transfer_requested": transfer_requested,
                "requested_amount_krw": amount,
                "customer_transfer_status": "UNCONFIRMED",
            }),
            ReportSection(section_key="verification_status", content={
                "status": "PENDING",
                "claims": diagnosis.context.claims,
            }),
            ReportSection(section_key="current_actions", content={
                "items": ["금융기관 담당자 확인 필요"],
                "human_decision_required": True,
            }),
            ReportSection(section_key="unresolved_items", content={
                "items": ["실제 송금 여부", "개인정보·인증정보 노출 여부", "상대방 주장 진위"],
            }),
            ReportSection(section_key="next_checks", content={
                "items": diagnosis.context.recommended_next_steps,
            }),
        ]
        return InitialReport(
            report_id=f"live-{case_id}", case_id=case_id, sections=sections,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
