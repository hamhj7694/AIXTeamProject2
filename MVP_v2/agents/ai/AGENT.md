# AI Agent

## Owns

- `MVP_v2/backend/ai_api/**`
- `MVP_v2/backend/contracts/ai_internal/**`
- future RAG corpus and retrieval adapters

## Responsibilities

- Perform sentence/window-level risk analysis and full-context analysis without directly mutating the database.
- Return structured, evidence-backed results to General API.
- Keep the Case creation threshold and uncertainty explicit.
- Design RAG responses as recommendations with sources, not fabricated institutional facts.

## Before handoff

- Provide fixture and failure behavior for local demos.
- State model mode, fallback behavior, evidence, confidence, and limitations.
