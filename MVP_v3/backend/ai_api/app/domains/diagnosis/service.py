from __future__ import annotations

import hashlib

from contracts.diagnosis import AnalysisEnvelope, ContextResult, DiagnosisResult, WindowAnalysisResult
from request_trace import trace_stage

from .extractor import build_case_context_features, signal_context_payload
from .budget import diagnosis_budget_scope
from .full_context_llm import FullContextDiagnosisHandler
from .risk_fusion import DiagnosisFusion
from .window_ai import WindowAiAdapter
from .context_features import extract_case_context_features
from .semantic_atoms import merge_semantic_atoms
from .audit import audit_semantic_result
from .lexical_cues import attach_context_observation_lineage
from .relations import build_context_signals, build_semantic_relations
from .grouping import build_action_groups, build_conversation_episodes, build_entity_registry
from .envelope import envelope_from_extraction, window_result_from_envelope


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
        """Development/demo adapter. Production CSR analysis starts from an Envelope."""
        with diagnosis_budget_scope():
            envelope = await self._build_demo_envelope(text)
            return await self._analyze_envelope(envelope, case_id=case_id)

    async def build_demo_envelope(self, text: str) -> AnalysisEnvelope:
        """Simulate the external/on-device analyzer without retaining its text."""
        with diagnosis_budget_scope():
            return await self._build_demo_envelope(text)

    async def _build_demo_envelope(self, text: str) -> AnalysisEnvelope:
        with trace_stage("ai.demo_adapter.events_and_ml"):
            window_result: WindowAnalysisResult = await self.window_ai.analyze(text)
        with trace_stage("ai.demo_adapter.context_features"):
            context_features = await extract_case_context_features(text)
        event_context_features = build_case_context_features(window_result.events)
        context_features = context_features.model_copy(update={
            "amount_values_krw": event_context_features.amount_values_krw,
            "requested_amount_values_krw": event_context_features.requested_amount_values_krw,
        })
        semantic_atoms = merge_semantic_atoms(window_result.semantic_atoms, window_result.events)
        window_result = window_result.model_copy(update={"semantic_atoms": semantic_atoms})
        source_reference = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
        return envelope_from_extraction(
            window_result, context_features, source_reference=source_reference,
        )

    async def analyze_envelope(self, envelope: AnalysisEnvelope, case_id: str | None = None) -> DiagnosisResult:
        """Production CSR entry point. It accepts structured data and no source text."""
        with diagnosis_budget_scope():
            return await self._analyze_envelope(envelope, case_id=case_id)

    async def _analyze_envelope(self, envelope: AnalysisEnvelope, case_id: str | None = None) -> DiagnosisResult:
        window_result = window_result_from_envelope(envelope)
        context_features = attach_context_observation_lineage(
            envelope.context_features, window_result.semantic_atoms,
        )
        semantic_atoms = window_result.semantic_atoms
        payload = signal_context_payload(window_result.events, semantic_atoms=semantic_atoms)
        payload["case_context_features"] = context_features.model_dump(mode="json")
        payload["semantic_mentions"] = [item.model_dump(mode="json") for item in envelope.semantic_mentions]
        payload["envelope_metadata"] = {
            "source": envelope.source,
            "reference_time": envelope.reference_time,
            "timezone": envelope.timezone,
            "source_text_included": False,
        }
        with trace_stage("ai.context_summary"):
            context: ContextResult = await self.full_context_llm.analyze(payload)
        result = self.fusion.merge(
            window_result, context, case_id=case_id,
        )
        # Keep the independent context projection as the first additive
        # operation for backwards compatibility with existing adapters.
        result = result.model_copy(update={"case_context_features": context_features})
        update: dict[str, object] = {
            "semantic_mentions": envelope.semantic_mentions,
            "model_metadata": {
                **result.model_metadata,
                "analysis_entrypoint": "STRUCTURED_ANALYSIS_ENVELOPE",
                "analysis_envelope_version": envelope.schema_version,
                "analysis_source": envelope.source,
                "source_text_retention": "NONE",
            },
        }
        generated_relations = build_semantic_relations(semantic_atoms)
        relation_by_id = {item.relation_id: item for item in [*envelope.semantic_relations, *generated_relations]}
        semantic_relations = list(relation_by_id.values())
        context_signals = build_context_signals(semantic_atoms)
        conversation_episodes = build_conversation_episodes(semantic_atoms)
        action_groups = build_action_groups(semantic_atoms)
        entity_registry = build_entity_registry(semantic_atoms)
        if window_result.events or semantic_atoms:
            source_by_turn = {turn.turn_id: turn.normalized_summary for turn in envelope.turns}
            deterministic_audit = audit_semantic_result(
                window_result.events,
                semantic_atoms,
                semantic_relations,
                context_signals,
                source_by_turn,
            )
            update["semantic_audit"] = deterministic_audit
            # CSR has no raw transcript, so it must never attempt source-text
            # re-extraction. Ambiguous upstream structure remains reviewable.
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
