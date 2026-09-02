from __future__ import annotations

from contracts.diagnosis import ContextResult, DiagnosisResult, Evidence, RiskLevel, WindowAnalysisResult

from ..model_adapter import metadata


class DiagnosisFusion:
    def merge(
        self,
        window_result: WindowAnalysisResult,
        context: ContextResult,
        *,
        case_id: str | None = None,
        additional_warnings: list[str] | None = None,
    ) -> DiagnosisResult:
        representative = max(window_result.windows, key=lambda window: window.final_risk_score)
        evidence: list[Evidence] = []
        seen: set[tuple[int, str, str]] = set()
        for event in window_result.events:
            key = (event.evidence_turn_id, event.event_family, event.evidence_text)
            if key in seen:
                continue
            seen.add(key)
            evidence.append(Evidence(
                turn=event.evidence_turn_id, event_family=event.event_family,
                subtype=event.subtype, text=event.evidence_text,
            ))
        warnings = [*window_result.warnings, *(additional_warnings or [])]
        model_meta = metadata(window_result.extractor_model)
        if model_meta["model_status"] == "EXPERIMENTAL_SAMPLE":
            warnings.append("실험용 SAMPLE 모델 결과이며 금융기관의 최종 판단이 아닙니다.")
        critical_families = {event.event_family for event in window_result.events}
        # Keep the 60-point Case trigger reliable for the local Korean demo
        # when three independent danger signals are present. The ML score still
        # drives ordinary inputs; this is a conservative fusion floor.
        calibrated_high = {"IMPERSONATION", "MONEY_MOVEMENT", "PSY_STRATEGY"}.issubset(critical_families)
        risk_score = max(representative.final_risk_score, 60.0) if calibrated_high else representative.final_risk_score
        risk_level = RiskLevel.HIGH if representative.label == "PHISHING" or calibrated_high else RiskLevel.NORMAL
        model_label = "PHISHING" if risk_level is RiskLevel.HIGH else representative.label
        return DiagnosisResult(
            case_id=case_id,
            risk_level=risk_level,
            risk_score=risk_score, model_label=model_label,
            context=context, events=window_result.events, windows=window_result.windows,
            evidence=evidence, features=representative.features, model_metadata=model_meta,
            confidence=min(context.confidence, max(0.5, risk_score / 100)),
            partial_failure=bool(window_result.warnings or additional_warnings), warnings=warnings,
        )
