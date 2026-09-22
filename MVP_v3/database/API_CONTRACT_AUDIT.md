# CSR 프론트엔드·백엔드·DB 계약 대조

기준 시점: 2026-09-22 · 대상: `frontend/src/api`, 화면 호출부, General API 공개 contract, repository SQL, [`DB_CATALOG.md`](DB_CATALOG.md)

이 문서는 DB를 삭제하거나 migration을 실행하기 전에 **같은 의미의 데이터가 프론트엔드·백엔드·DB에서 같은 이름과 책임으로 연결되는지** 확인하는 선행 점검표다. 이 문서의 `[ ]`는 아직 수정·승인하지 않은 항목이며, 코드가 정상적으로 빌드된다는 뜻만으로 완료 처리하지 않는다.

## 1. 점검 결과 요약

- 현재 핵심 Frontend 호출 경로(`cases.ts`, `context-v3/api.ts`, `contextWorkspace.ts`, `EditableContext.tsx`)를 General API route와 대조했다. 호출 URL이 백엔드에 전혀 없는 즉시 장애는 확인되지 않았다.
- 다만 “경로가 존재한다”와 “계약이 완전히 일치한다”는 다르다. 타입에 빠진 응답 필드, DB에는 있지만 공개 API에서 숨기는 역할 필드, legacy Fact와 Context V2의 병렬 모델이 남아 있다.
- 따라서 현재 DB Catalog는 **현재 코드가 실제로 읽고 쓰는 구조를 기록한 스냅샷**이지, 코드 설계가 중복되지 않았다는 보증서가 아니다.
- DB 테이블·컬럼을 더 삭제하기 전에 아래 계약 불일치를 결정하고, 필요한 경우 코드·contract·migration을 같은 변경으로 묶어야 한다.
- 원문 입력은 `case_inputs.input_text`에 보관하되 최초 분석 결과 화면의 일시 확인 범위로 제한한다. 일반 Case read/list/bundle·Case Copilot·Context AI 응답에는 포함하지 않는다.

## 2. 계약 대조 매트릭스

| 영역 | 프론트엔드 | 백엔드 | DB | 판정 | 다음 조치 |
|---|---|---|---|---|---|
| Case 읽기 | `StoredCase`가 분석 상세를 타입으로 가짐 | `GET /cases/{id}`는 `diagnosis: dict`로 반환 | `cases.diagnosis_json`·semantic 테이블·report가 병존 | 부분 일치 | Case Read와 분석 상세의 authoritative source matrix 작성 |
| Case bundle | `CaseBundle.case`는 `Record<string, unknown>` | bundle은 `case`, `live_report`, `final_report`, `voice_session`을 반환 | summary/projection/report/session을 함께 조립 | 응답에 타입 누락 | 사용 필드와 호환 필드를 구분해 TS 타입을 보강하거나 응답에서 명시적으로 제외 |
| Legacy Fact | `CaseFact` 타입은 구버전 외부 호환용 | `/facts` 공개 API와 repository adapter 존재 | `case_context_facts_v2` (응답 변환) | 호환 adapter | V2 canonical, 외부 호출 0 확인 후 route/table deprecation |
| Context V2 | `contextWorkspace.ts`, `context-v3/api.ts`가 별도 타입 사용 | `/context-v2/*` 계약은 엄격한 V2 모델 | `case_context_facts_v2`, gaps, suggestions, tasks, decisions | 별도 모델이지만 연결 규칙 문서화 필요 | V2를 canonical source로 고정하고 legacy fallback만 허용 |
| 우측 Context Panel | 현재 `support.case_context`·Context Workspace 조립값을 사용 | 여러 원장에서 직원용 결과를 조립할 수 있음 | `live_report`, Context V2, 확인 업무·담당자 업무·projection | 표시 계약 미확정 | `live_report` JSON에 직접 결합하지 말고 표시용 계약을 먼저 확정 |
| 담당자 권한 | `CaseMember`에는 `assignment_role`만 있음 | `role`은 저장하지만 공개 응답에서 제거하고 `assignment_role`로 서버가 파생 | `case_members.role` + `assignment_role` | 의도된 이중 책임이나 UI에서 권한 역할 수정 불가 | “배정 역할→시스템 권한 파생”을 제품 계약으로 확정하거나 독립 편집 기능을 별도 설계 |
| 직원 직무 | `OTHER_VIEWER`, 테스트 사용자 전용 `BLACK` 사용 | 직원 계약은 `OTHER_VIEWER`, 색상은 `GREEN`~`GRAY` | DB CHECK도 직원 직무·색상을 제한 | 의도된 표현 차이 | `BLACK`은 API/DB 값이 아닌 테스트 사용자 전용 UI 값으로 고정하고, `OTHER_VIEWER→VIEWER` 매핑을 공개 계약에 명시 |
| 거래 금액 | `CaseTransaction.amount: number` | API `amount: float` | `DECIMAL(19,2)`; Case 요약은 `BIGINT` | 표현 정밀도 차이 | KRW는 정수로 고정할지, decimal 문자열로 전달할지 결정. 자동 합산 금지 유지 |
| 첨부 | 요청에 빈 `attachment_ids`, 응답에 빈 `attachments` 타입 유지 | 첨부 route는 410, 메시지 응답은 빈 배열 | 첨부 테이블 없음, `messages.attachments_json`만 호환 컬럼 | 의도된 호환 상태 | 핫픽스 마지막 단계에서 외부 소비자 확인 후 계약·컬럼 동시 제거 |
| 통화 세션 | 현재 핵심 화면 직접 호출 없음 | route와 bundle의 `voice_session` 계약 유지 | `voice_sessions` metadata | 호환 계약 | 저장소 검색·접근 로그·외부 클라이언트 확인 후 deprecation 판단 |

## 3. 중복처럼 보이지만 책임이 다른 데이터

### 3.1 Case 분석·Context·보고서

현재는 다음 네 층이 함께 존재한다.

1. `cases.diagnosis_json`: 분석 직후의 초기 분석 묶음
2. semantic/analysis 테이블: atom·relation·segment를 행 단위로 조회하는 상세 projection
3. `case_context_projections`: Context 결과를 재사용하는 캐시
4. `case_reports`·`case_report_sections`: LIVE/FINAL 보고서와 버전·감사 이력

`CaseBundle`의 `live_report`는 초기 분석 단계에서 저장된 LIVE 보고서 snapshot이고, `final_report`는 종결 시 생성되는 버전 보고서다. `voice_session`은 원문이 아니라 세션 상태 metadata다. 현재 프론트는 `bundle.case`, 대화·질문·업무·고객 진행 상태를 사용하지만 `live_report`와 `voice_session`을 직접 읽지는 않는다. 따라서 `live_report`를 우측 Context Panel 전체의 공개 계약으로 사용하지 않는다. 패널 항목이 확정되면 표시용 계약을 별도로 만들고, 그 계약을 `live_report`·Context V2·확인 업무 등에서 조립한다. 두 호환 필드를 삭제하려면 먼저 외부 클라이언트와 과거 화면이 없는지 확인하고, 삭제하지 않으면 프론트 타입에 optional 필드로 명시해야 한다.

내용이 일부 겹쳐 보여도 모두 같은 원본이라고 단정하면 안 된다. 먼저 필드별 authoritative source를 정한 다음 projection·cache를 재생성할 수 있는지 검증해야 한다.

### 3.2 Fact

`case_facts`와 `case_context_facts_v2`는 둘 다 사실 후보를 다뤘지만, V2가 근거·상태·확정자·이력을 더 풍부하게 표현한다. 현재 V2가 저장·조회 원본이며 `/facts`는 V2를 구형 응답으로 변환하는 호환 경로다. legacy 물리 테이블은 028에서 DROP 완료됐다.

전환 결과는 `V2 신규 write 고정 → 기존 Case 대응 키 검증 → /facts read를 V2 adapter로 변경 → 프론트 호출 제거 → legacy 행 0건 확인`까지 완료됐다. 남은 단계는 외부 호출량 0 확인 후 legacy API 410 및 물리 테이블 DROP이다.

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

- [ ] `CaseBundle`의 `case`를 공통 `CaseSummary` 타입으로 정의
- [ ] `live_report`는 초기 표시 보고서, `final_report`는 종결 보고서, `voice_session`은 세션 metadata라는 책임을 타입 주석과 계약 문서에 명시
- [ ] `live_report`, `voice_session`을 프론트 타입의 optional 필드로 포함할지, 외부 소비자 확인 후 응답에서 제거할지 결정
- [ ] `StoredCase.diagnosis`와 bundle `case`를 공통 `CaseSummary`/`CaseDiagnosis` 타입으로 정리
- [x] `case_facts`를 읽는 모든 route와 `case_context_facts_v2`를 읽는 route의 목록 확정
- [x] V2 신규 write 고정, `/facts` V2 adapter 전환, 대응 키 비교, legacy 행 0건 확인
- [ ] 외부 `/facts` 호출량 0 확인 후 410 전환 및 빈 호환 테이블 DROP
- [ ] 담당자 `role`을 배정 역할에서 계속 파생할지, 별도 수정 가능한 공개 필드로 만들지 결정
- [x] 테스트 사용자 색상 `BLACK`은 API/DB enum이 아닌 프론트 전용 표시값으로 명시
- [x] 직원 명부 `OTHER_VIEWER` → Case 멤버 `VIEWER` 매핑을 문서화
- [ ] 금액 API를 KRW 정수 또는 decimal 문자열 중 하나로 고정하고 FE·BE·DB 계약 테스트 추가
- [ ] 금액 계산 규칙 확정: 실제 거래 합계의 기준 테이블, `TRANSFER_OUT`·반환 거래 방향, 중복 거래 식별키, 시간대, 반올림·통화 단위
- [ ] `actual_loss_amount_krw`는 요약값으로만 유지하고 `case_transactions` 자동 합산·자동 승격을 금지한다. `case_transactions`는 실제 은행 원장이 아닌 데모 송금 기록 목록이며, `송금 기록 조회` 응답에 출처·확인 상태를 포함하는지 계약 테스트로 확인한다.
- [ ] 첨부 호환 필드와 `voice_session` 호환 필드의 외부 소비자 확인

### 4.1 호환 기능 제거 완료 조건

- [ ] `voice_sessions` route·SDK·배치·외부 클라이언트 검색 완료
- [ ] `voice_sessions` 접근 로그와 DB 최근 생성 시각 확인
- [ ] 외부 소비자 0건 확인 후 route를 410으로 전환하고 bundle 필드 제거 여부 승인
- [ ] `attachments`, `attachment_ids`, `attachments_json` 소비자 0건 확인
- [ ] 모든 메시지의 `attachments_json`이 NULL 또는 빈 배열인지 확인
- [ ] 첨부 API 410, 채팅, AI 지원, Case bundle 회귀 테스트 통과
- [ ] 백업·복원과 DB Catalog diff 승인 후에만 `messages.attachments_json` 제거 migration 실행

## 5. DB 삭제 판단과의 연결

아래 조건을 충족하기 전에는 관련 테이블·컬럼을 삭제하지 않는다.

- 프론트엔드 호출처가 새 endpoint/필드로 전환됨
- 백엔드 route와 repository가 같은 source of truth를 읽음
- 기존 응답과 새 응답을 Case별로 비교함
- 외부 클라이언트·배치·스크립트 호출이 없음
- 백업·복원과 회귀 테스트가 통과함
- `DB_CATALOG.md` 전후 diff를 승인함

특히 `case_facts`, `case_members.role`, `voice_sessions`, `messages.attachments_json`은 현재 코드 계약을 먼저 정리해야 하는 대상이다. DB에서 먼저 지우면 프론트·백엔드의 숨은 호환 경로가 깨질 수 있다. `BLACK`은 이 목록에 포함되지 않는다. 테스트 사용자 전용 프론트 표시값이며 DB/API 저장값이 아니기 때문이다.

## 6. 후순위 — 우측 Context Panel 설계 체크리스트

우측 패널의 최종 항목과 UI/UX가 확정되기 전에는 `live_report`의 특정 JSON 구조를 프론트 컴포넌트에 직접 결합하지 않는다. 먼저 직원 화면에 필요한 **표시용 계약**을 정의하고, 백엔드는 `live_report`·Context V2·확인 업무·담당자 업무 등 여러 원본에서 그 계약을 조립한다.

권장 순서는 다음과 같다.

- [ ] 우측 패널 UI/UX와 정보 우선순위 설계
- [ ] 각 섹션의 표시 항목·상태·빈 값·오류 상태 정의
- [ ] `live_report`에 종속되지 않은 표시용 TypeScript fixture/mock으로 프론트 프로토타입 구현
- [ ] 표시용 계약 확정: 예) `summary`, `customerExposure`, `scamSignals`, `offenderClaims`, `offenderDemands`, `manipulationTactics`, `verifications`, `customerProgress`, `activeTasks`
- [ ] 표시용 계약을 반환하는 Backend API와 source-of-truth 매핑 확정
- [ ] 기존 테이블/API로 충족되는지 확인한 뒤 필요한 경우에만 DB 컬럼·테이블·projection 변경
- [ ] 초기 분석(`live_report`)과 최신 Context 상태가 섞이지 않는지 회귀 테스트
- [ ] Case 생성→추가 채팅→직원 확인→고객 공유 결과 반영까지 패널 갱신 테스트
- [ ] `live_report` 구조 변경이 표시용 계약과 프론트 화면을 직접 깨뜨리지 않는지 계약 테스트

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
