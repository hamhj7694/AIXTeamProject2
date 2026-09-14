# Context Panel V3 구현 보고서

작성일: 2026-09-14  
기준 문서: `13_CONTEXT_PANEL_DATA_AUDIT.md`, `14_CONTEXT_PANEL_CONTRACT_PLAN.md`  
판정 기준: 실제 실행 코드 > DB/Schema > API > Frontend > AI > 설계 문서

## 1. 최종 구현 구조

```text
CUSTOMER/BANK_STAFF CHAT
  → General API Message DB commit
  → message_context_extractions (durable, max 3 attempts)
  → AI API /ai/context/facts/extract
  → General API contract/evidence validation
  → case_context_facts_v2 PROPOSED
  → Context V3 deterministic projection
  → GET /api/cases/{case_id}/context-v2/panel
  → frontend/src/context-v3/ContextPanelV3.tsx
```

AI는 화면 Section을 확정하지 않는다. 허용된 semantic key의 Fact proposal만 만들며, confirm/reject/supersede는 직원 command와 감사 이력으로 처리한다.

## 2. DB 변경

- `customer_questions`: 질문별 `allow_multi_select`, `question_version`, `answer_payload_json`, `answer_question_version` 추가.
- `message_context_extractions`: message 단위 멱등 job, 상태, 시도 횟수, 안전한 오류 요약, model/prompt version, 처리 시각 추가.
- 질문 payload 변경도 `context_revision`을 올리도록 trigger 확장.
- 기존 row 삭제·bulk rewrite 없음. `answer_text`는 사람용 snapshot과 legacy compatibility로 유지.

## 3. Migration

- Forward: `backend/migrations/015_context_panel_v3.sql`
- Rollback: `backend/migrations/rollback/015_context_panel_v3.sql`
- Baseline: `database/01_mysql_csr_schema.sql` 동기화.
- 격리된 임시 MySQL DB에서 전체 migration 적용, 015 rollback, 015 재적용을 자동 검증했다.

## 4. API 변경

- `GET /api/cases/{case_id}/context-v2/panel?view=bank|customer`
- `PATCH /api/cases/{case_id}/context-v2/facts/{fact_id}/review`의 `supersedes_fact_id`
- 고객 질문 답변의 `selected_option_ids + free_text + question_version`
- 기존 `raw_answer` 입력은 compatibility 경로로 유지.
- 기존 Fact/Gap/Suggestion/Task/Decision/Verification API는 삭제하지 않았다.

## 5. Message → Fact

- Message 저장 성공 뒤 extraction job을 enqueue한다.
- 대상은 `CUSTOMER`, `BANK_STAFF`의 `CHAT`뿐이다.
- agent/system/private/report/verification/AI response는 제외한다.
- message_id가 job 멱등키이며 `PENDING → PROCESSING → COMPLETED|FAILED`, 최대 3회다.
- AI 장애·계약 위반은 FAILED로 기록하고 원본 Message는 보존한다.
- dedupe는 message id + semantic key + normalized value 기반이다.

## 6. AI extraction

- 위치: `ai_api/app/domains/case_support/context_fact_extraction_service.py`
- 계약: `contracts/ai_internal/context_fact_extraction.py`
- 16개 허용 semantic key, key별 typed value 기본 검증, evidence message id, confidence를 강제한다.
- 결과에 CONFIRMED 상태가 없으며 General API는 항상 PROPOSED로 저장한다.
- OTP 요구/제공, 요청/실제 금액, 송금 상태, 검찰 사칭, 인물 역할, 원격 앱, CLAIM/DEMAND/TACTIC을 분리한다.

## 7. 질문 답변

- 선택지는 질문 id와 label로 안정적인 option id를 생성한다.
- 복수 선택과 직접 입력을 동시에 전송·저장한다.
- 현재 질문 version과 다르면 409, 존재하지 않는 option 또는 허용되지 않은 복수 선택은 422다.
- 화면 재조회 시 `answer_payload`와 `answer_question_version`을 반환한다.
- 구조화 payload가 canonical이며 `answer_text` delimiter를 다시 파싱하지 않는다.

## 8. 질문 중복 방지

- 확정 Fact, 기존 PENDING/ASKED/ANSWERED 질문을 먼저 제외한다.
- CUSTOMER_STATEMENT/STAFF_OBSERVATION PROPOSED가 있으면 재질문보다 직원 검토를 우선한다.
- 고객·직원 원문 CHAT에 명시된 답변도 conservative keyword guard로 중복 질문에서 제외한다.
- 그 뒤 deterministic/AI contextual 후보를 합치고 General API가 최종 안전·유사도 필터를 적용한다.

## 9. Verification

- 기존 `verification_tasks`가 authoritative store다.
- COMPLETED와 결과 요약이 함께 저장되면 `OFFICIAL_VERIFICATION / PROPOSED` Fact를 생성한다.
- 직원 confirm 전에는 확정되지 않는다. confirm 시 같은 semantic key Gap을 자동 resolve한다.
- 공식기관 corpus/credential은 저장소에 없어 `OfficialVerificationSource` interface, 비가용 provider, fixture test, TODO boundary만 추가했다. 검색 hit가 Verification 완료 상태를 만들 수 없다.

## 10. Task/Action

- 신규 일반 업무는 `case_tasks`를 사용한다.
- AI Suggestion은 직원 ACCEPT 뒤 transaction에서 TODO Task가 된다.
- V3 화면에서 직접 업무 추가, 시작, 결과를 포함한 완료, 사유를 포함한 취소가 가능하다.
- AI 추천만으로 COMPLETED가 되지 않는다.
- legacy Action은 Case control, 고객 진행 상태, 기존 데이터 compatibility 때문에 유지한다.

## 11. Customer Share

서버 allowlist에 다음만 포함한다.

- `CONFIRMED + CUSTOMER_SHARED` Fact
- `COMPLETED + customer_visible` Verification 결과
- `COMPLETED + RESULT_PUBLISHED` Task 결과
- UNKNOWN이 아닌 Customer Progress
- CUSTOMER visibility로 직원/Customer Agent가 보낸 공개 메시지

`BANK_INTERNAL`, `AI_PRIVATE`, proposed/rejected Fact, 내부 Task 설명·근거·AI metadata는 projection에 포함하지 않는다. Frontend 필터에 보안을 맡기지 않는다.

## 12. Frontend

- 신규 위치: `frontend/src/context-v3/`
- 정확한 7개 Section: 현재 사건 요약, 피해·노출, 사칭·접촉 정보, 사기 정황, 사실·확인 현황, 담당자 조치 및 결과, 고객 공유 결과.
- loading/empty/error/retry, projection status, proposed/confirmed 상태를 표시한다.
- Fact confirm/reject 및 scalar conflict 자동 supersede, 표시용 요약 편집, Verification 열기, Suggestion 채택/제외, Task 생성/시작/완료/취소를 연결했다.
- 제시 계좌·연락처는 은행 projection에서도 마스킹한다.
- 고객 질문 카드는 checkbox 복수 선택과 직접 입력을 동시에 유지한다.

## 13. Summary와 Display Override

- Summary는 canonical Fact가 아닌 3~5개 deterministic derived bullet이다.
- 동일 API revision으로 projection되며 외부 LLM 실패에 의존하지 않는다.
- 표시용 요약 edit는 canonical value를 변경하지 않는다.
- `override_scope`, `base_projection_revision`, `base_content_hash`, `updated_by`를 보존한다.
- base revision이 오래되면 편집본은 history에 남지만 최신 화면을 가리지 않는다.

## 14. Legacy 전환

- `CaseRoomPage`의 production render는 `ContextPanelV3`로 전환했다.
- `CaseContextPanel`, `ContextWorkspace`, `EditableContext` 파일과 기존 API/DB는 rollback·compatibility를 위해 남겼다.
- production Case Room에서 legacy panel import는 없다.
- legacy AI의 panel-oriented fields는 Diagnosis, Case Support, 기존 테스트·호환 응답이 아직 사용하므로 삭제하지 않고 legacy-only 호환 데이터로 유지했다.

## 15. Backward compatibility

- 기존 질문 `raw_answer`, `answer_text`, Context v2 API, legacy panel source, legacy Action/Diagnosis data를 유지한다.
- 새 reader는 old nullable question columns를 읽고 기본 question version 1로 정규화한다.
- 신규 메시지부터 Fact extraction이 적용되며 과거 전체 메시지 backfill은 하지 않는다.

## 16. 검증 결과

- General API 전체: 174 tests PASS. 질문별 다중선택 저장과 MySQL integration 포함.
- AI API 전체: 106 tests PASS.
- Frontend typecheck PASS.
- Frontend production build PASS, 1,459 modules.
- Frontend `test-*.cjs`: 기존 전체 + Context V3 정적 계약 검사 PASS.
- Migration: 격리 MySQL apply → rollback → reapply PASS.
- Python compile/contract/route/repository/visibility/vertical slice 검사 PASS.

최종 수치는 작업 종료 직전 전체 suite 재실행 결과가 우선한다.

## 17. E2E 시나리오 판정

| # | 시나리오 | 자동 검증 | 판정 |
|---|---|---|---|
| 1 | 고객 검찰+OTP 메시지 → 저장 → proposal → Section 2/3/4 | in-memory General↔AI vertical slice | PASS |
| 2 | 요청 500만원/실제 300만원 분리 | AI extraction unit | PASS |
| 3 | 복수 선택+직접 입력 저장, OTP/card 후보 | API contract + extractor unit | PASS(조합 테스트) |
| 4 | confirmed 보존, conflicting proposal, supersede history | Context v2 endpoint | PASS |
| 5 | Verification 완료→proposal→confirm→Gap resolve | route/repository tests 조합 | PASS(조합 테스트) |
| 6 | Suggestion→직원 채택→Task, 자동 완료 금지 | Context v2 endpoint | PASS |
| 7 | 고객 allowlist와 내부 정보 차단 | panel projection unit | PASS |
| 8 | 새로고침에 필요한 DB 영속 | MySQL repository + frontend reload contract | PASS(통합), 브라우저 미실행 |
| 9 | extraction 실패 시 Message 보존/FAILED/retry | General API failure path | PASS |

실제 브라우저를 구동해 9개를 연속 클릭하는 E2E는 실행하지 못했다. 따라서 전체 E2E 최종 등급은 PARTIAL이다.

## 18. 미완료·외부 의존·알려진 위험

- 실제 공식기관 RAG corpus, 은행/기관/통신사 API와 credential이 없다. interface boundary만 구현했다.
- 실제 인증 세션 없이 `MVP_OPEN_PERMISSIONS` 또는 actor parameter를 쓰는 현재 구조는 운영 인증이 아니다.
- 기존 모든 legacy message/answer의 자동 backfill은 없다.
- Verification 결과는 현재 공통 기관 확인 key로 proposal되며 업무별 semantic key/Gap 연결을 입력받는 일반화는 후속 과제다.
- Canonical Fact의 자유로운 typed value 수정 UI는 없다. 새 conflicting proposal 검토·supersede 경로를 사용한다.
- V3의 Task 입력 UX는 최소 prompt 기반이며 디자인 시스템형 modal 개선은 후속 가능하다.
- 브라우저 클릭·시각·접근성 E2E는 별도로 필요하다.
- TestClient httpx2, MySQL risk_score precision, VALUES() deprecation warning이 남아 있다.

## 19. 다음 단계

1. 실제 배포형 MySQL clone에서 migration과 기존 데이터 조회 smoke test.
2. 은행/고객 두 브라우저로 9개 시나리오 연속 E2E 및 새로고침 검증.
3. 인증 세션/RBAC 도입 전 고객용 panel endpoint 접근 계약 확정.
4. 공식 corpus가 승인되면 provenance·평가셋과 함께 provider 구현.
5. Canonical Fact typed edit dialog와 Task prompt UX 개선.

## Context V3 Completion

- Context V3 usable: YES (자동 검증 기준; 실제 브라우저 E2E 필요)
- DB migration ready: YES
- Message→Fact working: YES
- 7-section API working: YES
- 7-section Frontend working: YES
- Structured Question Answer working: YES
- Verification integration working: YES (외부 공식자료 검색 제외)
- Task flow working: YES
- Customer visibility protection tested: YES
- Refresh persistence tested: YES (MySQL/API 통합; 브라우저 refresh 미실행)
- Legacy UI switched out: YES
- Legacy underlying data safely retained: YES
- Backend tests: PASS
- Frontend build/typecheck: PASS
- E2E: PARTIAL (자동 vertical slice·통합 검증 통과, 실제 browser E2E 미실행)
