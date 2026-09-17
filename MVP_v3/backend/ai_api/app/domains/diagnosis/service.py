from __future__ import annotations

from contracts.diagnosis import ContextResult, DiagnosisResult, WindowAnalysisResult
from request_trace import trace_stage

from .extractor import build_case_context_features, signal_context_payload
from .budget import diagnosis_budget_scope
from .full_context_llm import FullContextDiagnosisHandler
from .risk_fusion import DiagnosisFusion
from .window_ai import WindowAiAdapter
from .context_features import extract_case_context_features
from .semantic_atoms import merge_semantic_atoms
from .audit import audit_semantic_result
from .audit_agent import review_semantic_audit, targeted_reextract_turns
from .lexical_cues import attach_context_observation_lineage
from .relations import build_context_signals, build_semantic_relations
from .grouping import build_action_groups, build_conversation_episodes, build_entity_registry


class DiagnosisService:
    def __init__(
        self,
        window_ai: WindowAiAdapter | None = None,
        full_context_llm: FullContextDiagnosisHandler | None = None,
        fusion: DiagnosisFusion | None = None,
    ) -> None:
        self.window_ai = window_ai or WindowAiAdapter()
        self.full_context_llm = full_context_llm or FullContextDiagnosisHandler()
        self.fusion = fusion or DiagnosisFusion()

    async def analyze(self, text: str, case_id: str | None = None) -> DiagnosisResult:
        with diagnosis_budget_scope():
            # Source text is transient: only the two extraction stages see it.
            with trace_stage("ai.events_and_ml"):
                window_result: WindowAnalysisResult = await self.window_ai.analyze(text)
            with trace_stage("ai.context_features"):
                context_features = await extract_case_context_features(text)
            # The independent context model does not receive raw money values.
            # Preserve the deterministic event-derived amount arrays alongside
            # its enum observations instead of collapsing them to max/sum only.
            event_context_features = build_case_context_features(window_result.events)
            context_features = context_features.model_copy(update={
                "amount_values_krw": event_context_features.amount_values_krw,
                "requested_amount_values_krw": event_context_features.requested_amount_values_krw,
            })
            # The context LLM receives codes and references, never raw utterances.
            payload = signal_context_payload(window_result.events)
            payload["case_context_features"] = context_features.model_dump(mode="json")
            with trace_stage("ai.context_summary"):
                context: ContextResult = await self.full_context_llm.analyze(payload)
        result = self.fusion.merge(
            window_result, context, case_id=case_id,
        )
        update: dict[str, object] = {"case_context_features": context_features}
        semantic_atoms = merge_semantic_atoms(
            window_result.semantic_atoms, window_result.events,
        )
        context_features = attach_context_observation_lineage(context_features, semantic_atoms)
        update["case_context_features"] = context_features
        semantic_relations = build_semantic_relations(semantic_atoms)
        context_signals = build_context_signals(semantic_atoms)
        conversation_episodes = build_conversation_episodes(semantic_atoms)
        action_groups = build_action_groups(semantic_atoms)
        entity_registry = build_entity_registry(semantic_atoms)
        if window_result.events or semantic_atoms:
            source_by_turn = {index: turn for index, turn in enumerate(window_result.turns, start=1)}
            deterministic_audit = audit_semantic_result(
                window_result.events,
                semantic_atoms,
                semantic_relations,
                context_signals,
                source_by_turn,
            )
            update["semantic_audit"] = deterministic_audit
            review = await review_semantic_audit(source_by_turn, semantic_atoms, deterministic_audit)
            if review is not None:
                update["semantic_audit_review"] = review
                retry_turns = list(review.missing_turns)
                retry_turns.extend(
                    atom.source_turn_id for atom in semantic_atoms
                    if atom.atom_id in deterministic_audit.mixed_atoms
                )
                if review.review_status == "REEXTRACTION_REQUIRED" and retry_turns:
                    recovered = await targeted_reextract_turns(source_by_turn, retry_turns)
                    if recovered:
                        semantic_atoms = merge_semantic_atoms(semantic_atoms + recovered, window_result.events)
                        semantic_relations = build_semantic_relations(semantic_atoms)
                        context_signals = build_context_signals(semantic_atoms)
                        update["semantic_audit"] = audit_semantic_result(
                            window_result.events, semantic_atoms, semantic_relations,
                            context_signals, source_by_turn,
                        )
        if semantic_atoms:
            update["semantic_atoms"] = semantic_atoms
        if semantic_relations:
            update["semantic_relations"] = semantic_relations
        if context_signals:
            update["context_signals"] = context_signals
        if conversation_episodes:
            update["conversation_episodes"] = conversation_episodes
        if action_groups:
            update["action_groups"] = action_groups
        if entity_registry:
            update["entity_registry"] = entity_registry
        return result.model_copy(update=update)
