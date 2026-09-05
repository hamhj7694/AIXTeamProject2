# Data Contracts

P0-003 health 계약 구현. Case 계약은 P1-001에서 구현/검증한다.
GET /health (AI), GET /api/v4/health (General): service, status=ok, contract_version=v4.health.1; extra 금지.
GET /ready (AI), GET /api/v4/ready (General): service, ready, checks. 의존 미준비 시 503.
AI liveness는 추론 준비/품질을 보장하지 않는다.
P0-006: GET AI /ready/ml → MlPreflight(service, capability=structured_feature_ml, ready=true,
artifact_sha256, model_status/version, sklearn_version, feature_count, checks.zero_features/signal_features).
이 endpoint는 실제 승인 모델로 두 합성 feature vector를 추론하며 DB/LLM/network 부작용은 없다.
hash/파일/버전/추론 검증 실패 시 503 + checks.ml=ML_PREFLIGHT_FAILED (경로나 exception 미공개).
GET AI /ready는 제품 전체 readiness: checks.ml=ok이어도 conversational/text_intake=NOT_IMPLEMENTED이면 503.
GET General /api/v4/ready도 AI_NOT_READY를 유지한다. Phase 0의 ML preflight 성공과 제품 준비를 구분한다.
Migration 001: application_metadata(key PK, value), alembic_version.
Migration 002: V4-owned `cases`, participants, structured context, message/question/fact/verification/task/progress,
AI suggestion/run, event/brief/report, personal data, attachment, official contact, idempotency key tables.
`actions` 같은 legacy 업무 원본은 생성하지 않는다. 신규 은행 업무 원본은 `tasks`다.
변경 Entity version, Case revision/fingerprint, write client_request_id(UUID), expected_version 불일치 409.
CUSTOMER/BANK_INTERNAL/AI_PRIVATE projection은 서버 강제. 고객 query의 view 값만으로 권한 부여 금지.
원문은 ML/feature 추출 중에만 일시 사용. Reconstruction에는 구조화 feature만 전달.

## P1-001 Shared Case contract

- `cases` is the one shared case record: `status`, `mode`, `loss_status`, `revision`, `fingerprint`, `version`.
- All mutable case-scoped entities have `case_id`, `version`, audit timestamps/actors, soft-delete field; visibility-bearing entities are constrained to CUSTOMER/BANK_INTERNAL/AI_PRIVATE.
- `case_events` is immutable audit history with actor, entity target, visibility and `case_revision`.
- `idempotency_keys` scopes a retry key by case and operation. P1-002 will use it before write side effects.
- `StructuredFeaturePayload` rejects source-text keys recursively. Feature-only intake mapping is P2 work.
- `expected_version`/409, actual authorization and role projection behavior are P1-002/P1-003 API work; schema alone does not grant access.

## P1-002 Case/Event/Projection API

- `POST /api/v4/cases` creates a case and participant set. A customer can create only for self; a bank staff actor must provide the customer participant ID. The UUID `client_request_id` deterministically identifies a retried create.
- `GET /api/v4/cases/{case_id}` returns a role projection. CUSTOMER receives only its participant record and CUSTOMER events; BANK_STAFF receives CUSTOMER and BANK_INTERNAL events. `AI_PRIVATE` is not an API projection.
- `POST /api/v4/cases/{case_id}/events` is BANK_STAFF-only, records an immutable Event and atomically advances Case revision/version/fingerprint. `AI_PRIVATE` writes are rejected.
- Actor identity is `ActorContext` attached by trusted server authentication middleware. No request body, query `view`, or client header selects actor role or grants a projection.
- A repeated `(case_id, client_request_id, CREATE_EVENT)` with identical request fingerprint returns the prior state. A changed payload for the same key, or a stale `expected_version`, returns 409.

## P2-001 Structured-feature ML intake

- `POST AI /intake/ml` accepts exactly the approved model feature names and calls the V4-only approved adapter. Feature order, threshold and guardrail remain in the model bundle.
- `POST General /api/v4/cases/{case_id}/intake/ml` accepts a source event ID, expected version and structured numeric feature vector. It never accepts or stores source text.
- General records one `context_features` row and one BANK_INTERNAL `CONTEXT_FEATURE` audit Event in one transaction, including result score/classification and model provenance; it advances Case revision/version/fingerprint once.
- Same source event and matching feature/result fingerprint is a no-op. Changed duplicate is 409, stale version is 409, invalid vectors are 422, and unavailable AI is 503 without a Case write.
