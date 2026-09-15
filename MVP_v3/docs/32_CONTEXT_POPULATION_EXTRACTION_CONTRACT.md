# Context Population·Message Extraction 계약 (Step 6)

작성일: 2026-09-15

## Initial Case → Fact

초기 Case 저장 후 `seed_initial_context_facts()`는 persisted diagnosis의 구조화 값만 canonical V2 Fact proposal로 승격한다. seed는 `PROPOSED`, `BANK_INTERNAL`, `source_kind=AI_EXTRACTION`이며 직원 검토 전 고객에게 공개되지 않는다.

| Signal | Source | semantic key | Section | 상태 |
|---|---|---|---|---|
| 실제 이체 여부 | `victim_transfer_status` | `transfer.actual.status` | EXPOSURE | seed 가능 |
| 요구 금액 | `features.requested_amount_max` | `transfer.requested.amount` | EXPOSURE | Step 6 보완 |
| 실제 이체 금액 | `actual_loss_amount_krw` + YES | `transfer.actual.amount` | EXPOSURE | Step 6 보완 |
| 상대방 주장 | `context.claims` | `offender.incident_claim` | FRAUD_CIRCUMSTANCES | seed 가능 |
| 상대방 요구 | `context.demands` | `circumstance.demand` | FRAUD_CIRCUMSTANCES | seed 가능 |
| 압박·조작 | `context.manipulation_tactics` | `circumstance.tactic` | FRAUD_CIRCUMSTANCES | seed 가능 |
| 인증정보 요구 | `case_context_features.requested_action_codes` | `exposure.authentication_information` | EXPOSURE | code가 있을 때만 |
| 원격제어 요구 | `requested_action_codes` | `device.remote_control_app` | EXPOSURE | code가 있을 때만 |

기관명·전화번호·계좌·OTP 실제 제공 여부 등 source field가 없는 값은 추측해 seed하지 않는다. 상대방의 범죄 연루 발언은 확인된 사실이 아니라 `offender.incident_claim` 제안으로 보존한다.

## Message → Fact

```text
Message 저장 → PENDING → PROCESSING claim → deterministic extractor
→ semantic/evidence validation → PROPOSED Fact → revision/projection
→ COMPLETED 또는 FAILED → attempts<3 bounded retry
```

현재 `/ai/context/facts/extract`는 LLM이 아니라 `ContextFactExtractionService`의 bounded deterministic extractor다. 기본 `model_version=deterministic-v1`이며 endpoint 이름은 호환성을 위해 유지한다.

proposal은 `ALLOWED_SEMANTIC_KEYS`에 포함되고 현재 message ID를 evidence로 참조해야 한다. dedupe key는 message ID·semantic key·정규화 value로 계산해 같은 메시지 재처리 시 중복 Fact를 만들지 않는다.

## Job 상태·진단

- `PENDING`: 저장됐지만 처리 전
- `PROCESSING`: worker가 claim
- `COMPLETED`: proposal 0개를 포함해 정상 종료
- `FAILED`: 오류 기록, attempts<3이면 retry 대상
- `SKIPPED`: 추출 대상이 아닌 메시지

`GET /api/cases/{case_id}/context-extractions/{message_id}`는 원문 없이 상태·attempts·오류·model/prompt version만 반환한다.

## Revision·충돌·Visibility

- canonical Fact 생성/변경만 context revision을 증가시킨다. retry count·provider 오류만으로 revision을 올리지 않는다.
- 기존 `CONFIRMED` Fact를 overwrite하지 않고 새 `PROPOSED` Fact와 evidence를 남긴다.
- AI/고객/직원 추출 Fact는 기본 `BANK_INTERNAL`; 직원 검토 후 명시적으로 `CUSTOMER_SHARED`로 전환한다.

## 제한 및 다음 단계

- deterministic extractor 품질 개선, LLM multi-label/hierarchical feature, relation graph, ML 재학습·threshold 변경, Verification RAG, Agent prompt 개선은 미구현이다.
- Frontend freeze 유지, DB migration 없음(`NO_NEW_MIGRATION`), 외부 OpenAI 호출 없음.

`STEP_6_COMPLETE` · `PREWORK_COMPLETE_READY_FOR_PARALLEL`

