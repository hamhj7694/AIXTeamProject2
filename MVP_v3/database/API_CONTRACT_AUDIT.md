# CSR 프론트엔드·백엔드·DB 계약 대조

기준 시점: 2026-09-22 · 대상: `frontend/src/api`, 화면 호출부, General API 공개 contract, repository SQL, [`DB_CATALOG.md`](DB_CATALOG.md)

이 문서는 DB를 삭제하거나 migration을 실행하기 전에 **같은 의미의 데이터가 프론트엔드·백엔드·DB에서 같은 이름과 책임으로 연결되는지** 확인하는 선행 점검표다. `[x]`는 완료, `[-]`는 시간 제한으로 보류·범위 제외, `[ ]`는 아직 미결정인 항목이다.

## 1. 점검 결과 요약

- 현재 핵심 Frontend 호출 경로(`cases.ts`, `context-v3/api.ts`, `contextWorkspace.ts`, `EditableContext.tsx`)를 General API route와 대조했다. 호출 URL이 백엔드에 전혀 없는 즉시 장애는 확인되지 않았다.
- 다만 “경로가 존재한다”와 “계약이 완전히 일치한다”는 다르다. 타입에 빠진 응답 필드, DB에는 있지만 공개 API에서 숨기는 역할 필드, legacy Fact와 Context V2의 병렬 모델이 남아 있다.
- 따라서 현재 DB Catalog는 **현재 코드가 실제로 읽고 쓰는 구조를 기록한 스냅샷**이지, 코드 설계가 중복되지 않았다는 보증서가 아니다.
- DB 테이블·컬럼을 더 삭제하기 전에 아래 계약 불일치를 결정하고, 필요한 경우 코드·contract·migration을 같은 변경으로 묶어야 한다.
- 원문 입력은 `case_inputs.input_text`에 보관하되 최초 분석 결과 화면의 일시 확인 범위로 제한한다. 일반 Case read/list/bundle·Case Copilot·Context AI 응답에는 포함하지 않는다.

## 1.1 실행 우선순위 체크리스트

삭제보다 계약과 사용처 확인을 먼저 수행한다. 각 단계의 미완료 항목을 남긴 채 다음 단계의 DB 삭제 migration으로 넘어가지 않는다.

### P0 — 기준 계약 고정 (완료)

- [x] `CaseSummary`·`CaseDiagnosis`·`CaseBundle` 타입 정렬
- [x] `live_report`·`voice_session` 책임과 원문 비노출 원칙 문서화
- [x] Context V2 workspace 백엔드 응답 모델과 프론트 리소스 타입 정렬
- [x] V2 신규 저장을 canonical source로 고정

### P1 — 현재 진행할 계약 결정

- [x] 금액 표현을 KRW 정수로 확정하고 소수점 입력을 거부
- [x] 첫 송금·추가 송금·반환·취소의 거래 방향과 중복 식별 규칙을 확정. 원천 ID 우선, 현재 데모는 복합키 사용
- [x] `actual_loss_amount_krw`와 `case_transactions`의 책임을 분리하고 자동 합산 금지 규칙을 문서화
- [x] `StoredCase` read 응답과 Case summary/diagnosis 기준 원본 매트릭스 작성 — [`AUTHORITATIVE_SOURCE_MATRIX.md`](AUTHORITATIVE_SOURCE_MATRIX.md)
- [-] `case_members.role` 독립 편집 결정 — 현재 배정 역할→권한 파생 계약 유지

### P2 — 사용처 확인 후 호환 경로 전환

- [x] `/facts` 프론트 호출 제거 및 공개 route 410 전환
- [-] 외부 SDK·배치의 `/facts` 호출량 확인 및 호환 메서드 삭제 — 공개 route 410, 내부 호환 코드 보존
- [-] `voice_sessions`·첨부 호환 경로 deprecation — 이번 범위 제외
- [x] V2 전환 관련 프론트·백엔드 핵심 회귀 및 TypeScript 검사 완료

### P3 — 직원용 표시 계약 설계

- [-] 우측 Context Panel 표시 계약 — 제품 UI 확정 후 진행

### P4 — 데이터 보존 후 정리

- [-] 사용량 0·백업·복원·DB 삭제 migration — 이번 단계에서 DB 삭제 없음

## 2. 계약 대조 매트릭스

| 영역 | 프론트엔드 | 백엔드 | DB | 판정 | 다음 조치 |
|---|---|---|---|---|---|
| Case 읽기 | `StoredCase`가 분석 상세를 타입으로 가짐 | `GET /cases/{id}`는 `diagnosis: dict`로 반환 | `cases.diagnosis_json`·semantic 테이블·report가 병존 | 기준 원본 문서화 완료 | [`AUTHORITATIVE_SOURCE_MATRIX.md`](AUTHORITATIVE_SOURCE_MATRIX.md) 기준으로 projection/cache 재생성 검증 |
| Case bundle | `CaseBundle.case`를 공개 `CaseSummary`로 구체화했고 `live_report`·`voice_session`은 optional 타입으로 보강 | bundle은 `case`, `live_report`, `final_report`, `voice_session`을 반환 | summary/projection/report/session을 함께 조립 | 타입 정합성 보강 완료 | 화면 표시 계약은 별도로 확정 |
| Legacy Fact | 구버전 응답 타입 제거 완료 | `/facts`는 410 종료 응답만 제공 | `case_context_facts_v2` | 없음(내부 호환 메서드는 정리 대기) | V2 canonical, 외부 소비자 0 확인 후 호환 메서드 삭제 |
| Context V2 | `contextWorkspace.ts`가 V2 리소스 전체 필드, `context-v3/api.ts`가 명령 계약 사용 | `/context-v2/*`는 V2 리소스 강타입과 `PublicContextWorkspaceResponse`를 사용 | `case_context_facts_v2`, gaps, suggestions, tasks, decisions | 프론트·백엔드 workspace 계약 정합 | V2 canonical 유지, legacy fallback만 허용 |
| 우측 Context Panel | 현재 `support.case_context`·Context Workspace 조립값을 사용 | 여러 원장에서 직원용 결과를 조립할 수 있음 | `live_report`, Context V2, 확인 업무·담당자 업무·projection | 표시 계약 미확정 | `live_report` JSON에 직접 결합하지 말고 표시용 계약을 먼저 확정 |
| 담당자 권한 | `CaseMember`에는 `assignment_role`만 있음 | `role`은 저장하지만 공개 응답에서 제거하고 `assignment_role`로 서버가 파생 | `case_members.role` + `assignment_role` | 의도된 이중 책임이나 UI에서 권한 역할 수정 불가 | “배정 역할→시스템 권한 파생”을 제품 계약으로 확정하거나 독립 편집 기능을 별도 설계 |
| 직원 직무 | `OTHER_VIEWER`, 테스트 사용자 전용 `BLACK` 사용 | 직원 계약은 `OTHER_VIEWER`, 색상은 `GREEN`~`GRAY` | DB CHECK도 직원 직무·색상을 제한 | 의도된 표현 차이 | `BLACK`은 API/DB 값이 아닌 테스트 사용자 전용 UI 값으로 고정하고, `OTHER_VIEWER→VIEWER` 매핑을 공개 계약에 명시 |
| 거래 금액 | `CaseTransaction.amount: number`(KRW 정수) | API `amount: StrictInt`, 거래 종류 `TRANSFER_OUT/RETURN_IN/CANCELLED` | migration 029 이후 `BIGINT` + 비음수·종류 CHECK; Case 요약은 `BIGINT` | 계약 정렬 완료 | 중복 식별키는 원천 ID 우선, 없으면 데모 복합키 사용. 자동 합산 금지 유지 |
| 첨부 | 요청에 빈 `attachment_ids`, 응답에 빈 `attachments` 타입 유지 | 첨부 route는 410, 메시지 응답은 빈 배열 | 첨부 테이블 없음, `messages.attachments_json`만 호환 컬럼 | 의도된 호환 상태 | 핫픽스 마지막 단계에서 외부 소비자 확인 후 계약·컬럼 동시 제거 |
| 통화 세션 | 현재 핵심 화면 직접 호출 없음 | route와 bundle의 `voice_session` 계약 유지 | `voice_sessions` metadata | 호환 계약 | 저장소 검색·접근 로그·외부 클라이언트 확인 후 deprecation 판단 |

## 3. 중복처럼 보이지만 책임이 다른 데이터

### 3.1 Case 분석·Context·보고서

현재는 다음 네 층이 함께 존재한다.

1. `cases.diagnosis_json`: 분석 직후의 초기 분석 묶음
2. semantic/analysis 테이블: atom·relation·segment를 행 단위로 조회하는 상세 projection
3. `case_context_projections`: Context 결과를 재사용하는 캐시
4. `case_reports`·`case_report_sections`: LIVE/FINAL 보고서와 버전·감사 이력

`CaseBundle`의 `live_report`는 초기 분석 단계에서 저장된 LIVE 보고서 snapshot이고, `final_report`는 종결 시 생성되는 버전 보고서다. `voice_session`은 원문이 아니라 세션 상태 metadata다. 현재 프론트는 `bundle.case`, 대화·질문·업무·고객 진행 상태를 사용하지만 `live_report`와 `voice_session`을 직접 읽지는 않는다. 프론트 `CaseBundle`에는 두 필드를 optional로 반영했으며, 이는 응답 계약을 맞추기 위한 타입 보강일 뿐 화면 노출이나 우측 패널 연결을 의미하지 않는다. 따라서 `live_report`를 우측 Context Panel 전체의 공개 계약으로 사용하지 않는다. 패널 항목이 확정되면 표시용 계약을 별도로 만들고, 그 계약을 `live_report`·Context V2·확인 업무 등에서 조립한다. 두 호환 필드를 삭제하려면 먼저 외부 클라이언트와 과거 화면이 없는지 확인해야 한다.

내용이 일부 겹쳐 보여도 모두 같은 원본이라고 단정하면 안 된다. 먼저 필드별 authoritative source를 정한 다음 projection·cache를 재생성할 수 있는지 검증해야 한다.

### 3.2 Fact

`case_facts`와 `case_context_facts_v2`는 둘 다 사실 후보를 다뤘지만, V2가 근거·상태·확정자·이력을 더 풍부하게 표현한다. 현재 V2가 유일한 저장·조회 원본이며, `/facts` 공개 route는 410으로 종료됐다. legacy 물리 테이블은 028에서 DROP 완료됐다.

전환 결과는 `V2 신규 write/read 고정 → 기존 Case 대응 키 검증 → 프론트 호출 제거 → legacy 행 0건 확인 → /facts 410 전환`까지 완료됐다. 남은 단계는 외부 호출량 0 확인 후 내부 호환 메서드를 삭제하는 일이다.

#### Fact 통합 대응표 — `case_context_facts_v2` 기준

| legacy `case_facts` | V2 `case_context_facts_v2` | 변환 규칙 | 확인 조건 |
|---|---|---|---|
| `fact_id` | `fact_id` | 길이 제한을 지키기 위해 `legacy-` + `SHA256(case_id:fact_id)` 결정적 ID 사용 | 재실행해도 중복 생성되지 않음 |
| `case_id` | `case_id` | 그대로 복사 | 대상 Case가 존재해야 함 |
| `field_name` | `semantic_key` | 허용 목록으로 매핑. 예: `authentication_information_exposure` → `exposure.authentication_information`, `personal_information_exposure` → `exposure.personal_information` | 매핑되지 않은 값은 임의 변환하지 않고 격리 |
| `value` | `value_json`, `display_value` | 구조화 가능한 값은 JSON으로 저장하고 표시용 문자열은 원문 의미를 보존 | 값이 사라지거나 자동 확정되지 않음 |
| `source` | `source_kind` | `AI_EXTRACTED` → `AI_EXTRACTION`처럼 명시적 매핑만 허용 | 알 수 없는 source는 마이그레이션 중단 |
| `status` | `status` | `PROPOSED/CONFIRMED/REJECTED/SUPERSEDED`만 허용 | 상태를 확정으로 승격하지 않음 |
| `confidence` | `confidence` | 정밀도와 범위를 유지 | 0~1 범위 검증 |
| `evidence_message_id`·`source_question_id` | `evidence_refs_json` | 메시지·질문 ID를 타입이 있는 근거 객체로 보존 | 근거 ID를 문자열 설명으로만 합치지 않음 |
| `confirmed_by`·`confirmed_at` | 같은 이름의 V2 필드 | 확정 상태일 때만 복사 | 확인자·시각 누락 시 확정 금지 |
| `created_at` | `created_at`·`updated_at` | 최초 생성 시각 보존, migration 실행 시각으로 덮어쓰지 않음 | 감사 이력의 시간 순서 보존 |

중복 판정 키는 `case_id + semantic_key + 정규화된 value + 근거 집합 + source_kind + status`로 정의한다. `case_id + semantic_key`만으로 합치면 한 사건의 여러 요구·주장·노출 정황을 잃을 수 있다. 같은 의미라도 근거가 다르면 별도 Fact로 보존하고, 명백한 동일 행만 idempotent하게 병합한다.

### 3.3 담당자 역할

`case_members.role`은 현재 권한 검사 내부용이고, `assignment_role`은 화면의 업무 배정 역할이다. 서버는 배정 역할을 받아 `CASE_OWNER`, `REVIEWER`, `CHAT_OPERATOR`, `VIEWER`로 파생한다. 따라서 지금의 두 컬럼은 완전한 중복은 아니지만, 독립적인 권한 역할을 직원이 직접 수정하는 계약은 아직 구현돼 있지 않다.

현재 제품 계약은 **배정 역할을 입력하고 시스템 권한 역할은 서버가 파생하는 방식**이다. 독립 권한 역할 수정이 필요해지면 별도 API·권한 검증·감사 이벤트를 함께 설계해야 하며, 그 전에는 `role` 컬럼을 제거하지 않는다.

## 4. 반드시 결정해야 하는 계약 이슈

- [x] `CaseBundle`의 `case`를 백엔드 `PublicCaseSummaryResponse`와 대응하는 공통 `CaseSummary` 타입으로 정의
- [x] `live_report`는 초기 표시 보고서, `final_report`는 종결 보고서, `voice_session`은 세션 metadata라는 책임을 타입 주석과 계약 문서에 명시
- [x] `live_report`, `voice_session`을 프론트 `CaseBundle` optional 필드로 반영. 현재 화면에는 직접 표시하지 않으며, 우측 패널은 별도 표시용 계약을 사용한다.
- [x] `StoredCase.diagnosis`를 공통 `CaseDiagnosis`로 분리하고, bundle `case`는 `CaseSummary`로 정리
- [x] `/context-v2/workspace`에 `PublicContextWorkspaceResponse`를 적용하고 V2 리소스 목록을 강타입으로 검증
- [x] 프론트 `ContextWorkspaceData`의 facts/gaps/suggestions/tasks/decisions/evidence 필드를 백엔드 V2 계약과 정렬
- [x] `case_facts`를 읽는 모든 route와 `case_context_facts_v2`를 읽는 route의 목록 확정
- [x] V2 신규 write/read 고정, 대응 키 비교, legacy 행 0건 확인
- [x] 외부 프론트 호출 제거 및 `/facts` 410 종료 응답 추가
- [-] 외부 SDK·배치 호출량 0 확인 후 내부 호환 메서드 삭제 — 후속 정리
- [-] 담당자 `role` 독립 편집 여부 — 현재 계약 유지
- [x] 테스트 사용자 색상 `BLACK`은 API/DB enum이 아닌 프론트 전용 표시값으로 명시
- [x] 직원 명부 `OTHER_VIEWER` → Case 멤버 `VIEWER` 매핑을 문서화
- [x] 금액 API를 KRW 정수로 고정하고 소수점 입력을 거부하도록 FE·BE·DB 계약 반영
- [x] 거래 종류를 `TRANSFER_OUT`·`RETURN_IN`·`CANCELLED`로 고정하고 방향 의미를 문서화
- [x] `actual_loss_amount_krw`는 요약값으로만 유지하고 `case_transactions` 자동 합산·자동 승격을 금지한다. `case_transactions`는 실제 은행 원장이 아닌 데모 송금 기록 목록이며, `송금 기록 조회` 응답에 출처·확인 상태를 포함하는지 계약 테스트로 확인한다.
- [x] 중복 거래 식별키 확정: 원천 이벤트 ID가 있으면 `source + source_event_id`를 우선 사용하고, 현재 데모는 `case_id + transaction_type + transaction_at(UTC) + amount + account_number + counterparty_account` 정규화 조합을 사용한다. 두 계좌 식별자가 모두 없으면 자동 병합하지 않고 중복 후보로만 취급한다.
- [x] 기존 `TRANSFER_OUT` 기록과 고객 채팅 금액이 다르면 기존 거래를 덮어쓰거나 자동 추가하지 않는다. `transfer.amount_conflict` Context V2 제안과 “추가 송금인지 금액 착오인지” 재확인 질문을 만들고, 답변 전까지 기존 거래를 기준으로 유지한다.
- [x] 고객 발화 금액이 기존 거래와 같아도 “또 보냈다·추가로 보냈다” 가능성을 배제하지 않는다. 같은 금액의 재진술인지 추가 송금인지 애매하면 동일한 재확인 절차를 적용하고 자동 확정하지 않는다.
- [x] `case_transactions`는 외부 은행 원장이 아닌 Case 내부의 확인된 거래 기록으로 정의한다. Context V2의 `transfer.actual.amount` 사실이 직원 확인(`CONFIRMED`)된 경우에만 `TRANSFER_OUT` 또는 `RETURN_IN` 행으로 승격하며, 요구·약속·미확인 진술은 거래 행으로 만들지 않는다.

`actual_loss_amount_krw`는 `cases` 테이블의 nullable 사건 요약 컬럼이고, `case_transactions`는 여러 건의 거래 원장이다. 두 구조를 하나로 합치지 않는다. 거래별 출처·시각·상대방과 사건 단위의 담당자 확인 금액은 서로 다른 책임이므로, 한쪽의 추가·수정이 다른 쪽을 자동으로 덮어쓰지 않도록 분리한다.
- [-] 첨부 호환 필드와 `voice_session` 호환 필드의 외부 소비자 확인 — 이번 범위 제외

### 4.1 호환 기능 제거 완료 조건(후순위)

- [-] `voice_sessions`·첨부 소비자 확인 및 route/컬럼 제거 — 긴급 삭제 대상이 생길 때 재개

## 5. DB 삭제 판단과의 연결

아래 조건을 충족하기 전에는 관련 테이블·컬럼을 삭제하지 않는다.

- 프론트엔드 호출처가 새 endpoint/필드로 전환됨
- 백엔드 route와 repository가 같은 source of truth를 읽음
- 기존 응답과 새 응답을 Case별로 비교함
- 외부 클라이언트·배치·스크립트 호출이 없음
- 백업·복원과 회귀 테스트가 통과함
- `DB_CATALOG.md` 전후 diff를 승인함

특히 `case_facts`, `case_members.role`, `voice_sessions`, `messages.attachments_json`은 현재 코드 계약을 먼저 정리해야 하는 대상이다. DB에서 먼저 지우면 프론트·백엔드의 숨은 호환 경로가 깨질 수 있다. `BLACK`은 이 목록에 포함되지 않는다. 테스트 사용자 전용 프론트 표시값이며 DB/API 저장값이 아니기 때문이다.

## 6. 후순위 — 우측 Context Panel 설계 체크리스트(보류)

우측 패널의 최종 항목과 UI/UX가 확정되기 전에는 `live_report`의 특정 JSON 구조를 프론트 컴포넌트에 직접 결합하지 않는다. 먼저 직원 화면에 필요한 **표시용 계약**을 정의하고, 백엔드는 `live_report`·Context V2·확인 업무·담당자 업무 등 여러 원본에서 그 계약을 조립한다.

- [-] 우측 패널 UI/UX·표시 계약·API·DB 변경·회귀 테스트 — 제품 화면 확정 후 한 번에 진행

이 순서에서는 `live_report`는 초기 분석 영역의 입력 자료일 뿐이며, 우측 패널 전체의 공개 계약이 아니다.

## 7. 재검증 명령

```powershell
# Frontend가 호출하는 API 경로를 확인
rg -n "request<|/api/|contextUrl" MVP_v3/frontend/src -g '*.ts' -g '*.tsx'

# Backend 공개 route와 계약 확인
rg -n '^@app\.' MVP_v3/backend/general_api/app/main.py
rg -n '^class Public|^Message|^CaseAssignmentRole' MVP_v3/backend/contracts/public_api -g '*.py'

# Repository가 실제로 읽고 쓰는 컬럼 확인
rg -n 'SELECT |INSERT INTO|UPDATE |DELETE FROM' MVP_v3/backend/general_api/app/domains/cases -g '*.py'

# DB 실제 구조·행 수·FK 확인
MVP_v3/.venv/Scripts/python.exe MVP_v3/backend/scripts/inspect_database.py --output MVP_v3/backend/data/db-current.json
MVP_v3/.venv/Scripts/python.exe MVP_v3/backend/scripts/export_database_catalog.py
```

이 명령은 삭제를 수행하지 않는다. 결과를 이 문서의 매트릭스와 `DB_USAGE_AUDIT.md`에 반영한 뒤에만 다음 migration을 검토한다.
