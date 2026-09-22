# DB 사용처·정리 감사

기준 문서: [`DB_CATALOG.md`](DB_CATALOG.md)
기준 시점: 2026-09-22 02:27 UTC · `csr` 로컬 데모 DB 32개 테이블 / 356개 컬럼

이 문서는 스키마를 바로 삭제하기 위한 문서가 아니다. 실제 REST route, repository SQL, Frontend 호출처, Case bundle·Context Panel 조립 경로를 대조해 **현재 사용처를 분류하고, 이번 단계에서 안전하게 제거·전환할 수 있는 범위**를 확정한다. 프론트엔드·백엔드·DB 필드 의미의 불일치와 계약 결정 항목은 [API_CONTRACT_AUDIT.md](API_CONTRACT_AUDIT.md)에서 별도로 추적한다.

## 결론

1. **즉시 제거·전환 완료**
   - `transcript_segments`와 통화 세션별 원문 구간 저장 경로를 retirement 했다.
   - `GET/POST /api/cases/{case_id}/voice-sessions/{session_id}/transcript`는 `410 TRANSCRIPT_STORAGE_DISABLED`를 반환한다.
   - 데모 입력 원문은 `case_inputs.input_text`에 보관한다. 최초 분석 결과 화면에서만 일시적으로 확인하고 일반 Case read/list/bundle·Case Copilot/Context AI에는 반환하지 않는다.
   - `voice_sessions` 자체는 원문이 아닌 세션 상태·참여자 metadata만 보관하므로 당장 삭제하지 않는다.
   - 데모 범위에서 첨부파일을 제외했다. 업로드/목록/다운로드 API는 `410 ATTACHMENTS_DISABLED`로 전환했고 채팅 입력의 첨부 버튼을 제거했다.
   - `case_attachments`와 `message_attachments`는 행 수를 확인한 뒤 026 fail-closed migration으로 삭제했다.
   - 기존 `messages.attachments_json` 컬럼과 응답의 빈 `attachments` 배열은 구버전 클라이언트 호환을 위해 당분간 빈 값으로만 유지한다. 컬럼 삭제는 핫픽스 안정화 이후 마지막 계약 변경 단계에서 다룬다.
2. **현재 삭제하면 안 되는 영역**
   - 사건 원장·분석(`cases`, `case_inputs`, `analysis_segments`, `context_features`, semantic tables)
   - 대화·질문·거래(`messages`, `customer_questions`, `case_transactions`, `message_context_extractions`)
   - 현재 Context V2와 담당자·업무 화면이 읽고 쓰는 테이블
   - 보고서·이력·감사(`case_reports`, `case_report_sections`, `case_events`, history tables)
3. **다음 정리 단계 후보**
   - `case_facts`(legacy)와 `case_context_facts_v2`의 단일 canonical source 전환 **완료**. 027에서 지원 필드를 V2로 복사했고 028에서 legacy 행을 정리한 뒤 유지보수 창에서 물리 테이블도 DROP했다.
   - `cases.diagnosis_json`·분석 projection·report JSON의 중복 범위 축소
   - `case_context_projections.last_success_payload` 캐시 보존 기간/재생성 정책
   - `voice_sessions` metadata API의 실제 외부 소비자 확인 후 유지 또는 명시적 deprecation

첨부 테이블은 빈 상태를 확인한 뒤에만 DROP했다. 그 외 백업·데이터 이동·컬럼 삭제는 원장 보존과 회귀 안전성을 확인한 뒤 별도 단계에서 수행한다.

## 사용처 분류 기준

| 분류 | 의미 | 조치 |
|---|---|---|
| 핵심 원장 | Case·대화·거래처럼 화면과 업무 판단의 기준이 되는 데이터 | 유지, 삭제 금지 |
| 활성 projection | 원장으로부터 만든 분석/Context/보고서 읽기 모델 | 유지, 생성·갱신 경로 추적 |
| 선택 기능 | 현재 행 수가 0이어도 route/repository/UI 계약이 존재하는 기능 | 유지, 미사용을 삭제 근거로 삼지 않음 |
| 호환/legacy | 구 버전 API·데이터와의 호환에 필요한 경로 | 호출처 확인 후 단계적 전환 |
| 제거 완료 | 현재 제품 경계와 충돌하며 별도 호출처가 없는 경로 | 410 또는 fail-closed migration |

## 용어를 쉽게 풀어쓴 핵심 설명

### `case_facts`와 `case_context_facts_v2`

- `case_facts`는 먼저 만들어진 단순 사실 후보 장부다. 질문 답변이나 예전 AI 경로가 읽는 하위 호환 모델이다.
- `case_context_facts_v2`는 현재 Context 화면을 위한 확장 장부다. 값의 JSON 구조, 근거 메시지, 제안/확정/기각/대체 상태와 변경 이력을 함께 가진다.
- 둘 다 “사건에 대해 알고 있는 사실 후보”라는 점은 같지만, V2가 더 많은 상태와 근거를 표현한다. 지금 즉시 하나를 지우면 예전 API가 깨질 수 있으므로 V2를 기준으로 쓰기 전환→검증→legacy 종료 순서가 필요하다.

### `voice_sessions`

통화 녹음 파일이나 통화 원문을 저장하는 테이블이 아니다. 세션 ID, 시작/종료 상태, 참여자 metadata처럼 “통화 세션이 열려 있었는가”를 나타내는 호환용 상태 장부다. 현재 프론트엔드 핵심 화면의 직접 호출은 확인되지 않았지만 General API route와 Case bundle 응답 계약이 남아 있다. 따라서 DB 행이 0건이라는 이유만으로 삭제하지 않고, 저장소·외부 클라이언트·API 접근 로그를 확인한 뒤 deprecation 여부를 결정한다. 원문 구간은 이미 저장·조회 경로를 폐기했다.

#### `voice_sessions` 외부 소비자 확인 방법

아래 네 가지를 모두 확인해야 “외부 소비자 없음”으로 판정한다.

1. 저장소 검색: `voice-sessions`, `voice_session`, `voiceSession`의 route·SDK·프론트 호출처를 검색한다.
2. API 접근 로그: General API와 reverse proxy 로그에서 `POST/PATCH /api/cases/*/voice-sessions` 호출자·최근 호출 시각을 확인한다.
3. bundle 소비처: `voice_session` 필드를 읽는 웹·모바일·배치 클라이언트를 확인한다. 현재 저장소 프론트엔드 직접 소비처는 없다.
4. DB 상태: `voice_sessions` 행 수와 최근 `created_at`을 확인한다. 0행은 보조 증거이며 단독 삭제 근거가 아니다.

호출처·최근 로그·bundle 소비처가 모두 0이면 deprecation PR을 만들고, route `410` 전환 → bundle 필드 제거 → 테이블 DROP 순서로 별도 승인한다.

### `diagnosis_json`, semantic tables, projection/report JSON

- `cases.diagnosis_json`: 분석 직후 Case에 남기는 초기 분석 묶음(요약·정황·window 등)이다.
- `case_semantic_atoms`·`case_semantic_relations`·`analysis_segments` 등: 역할·행동·관계·구간을 행 단위로 조회할 수 있게 풀어 놓은 상세 projection이다.
- `case_context_projections`: Context 생성 결과를 빠르게 재사용하는 캐시와 lease/revision 상태다.
- `case_reports`·`case_report_sections`: 직원이 보는 LIVE/FINAL 보고서 원장과 섹션별 버전·감사 데이터다.

서로 같은 JSON을 무작정 네 번 저장하는 구조라기보다 “초기 분석 원본 묶음 / 조회 가능한 상세 / 재생성 캐시 / 버전이 있는 보고서”의 책임이 다르다. 데모에서 하나로 줄일 수는 있지만 검색·부분 갱신·이력·캐시 복구를 잃게 되므로, 먼저 authoritative field matrix를 정한 뒤 선택적으로 축소한다.

### 금액과 `송금 기록 조회`

이번 데모에서는 실제 은행·계좌 원장 API를 연결하지 않는다. `case_transactions`는 Case 최초 분석, 고객·직원 채팅, 직원의 데모 확인 입력에서 만든 **표시용 송금 기록**을 담는 목록이며, 은행 시스템에서 확인된 거래라는 의미가 아니다. `송금 기록 조회` 카드는 이 목록을 이용해 기록을 보여주되 각 항목의 출처와 확인 상태를 함께 표시한다.

`cases.actual_loss_amount_krw`는 사건 전체를 한 숫자로 요약하는 값이다. 분석에서 언급된 금액, 송금 요청, 고객의 송금 진술을 자동으로 실제 거래로 승격하거나 합산하지 않으며, 직원이 데모 확인한 값만 별도 상태로 남긴다. 카드에서는 최소한 `거래 없음`, `조회 실패`, `미확인`, `송금 진술`, `데모 확인`을 구분한다.

데모 기록은 `case_id`와 원천 이벤트/메시지 식별자를 기준으로 중복을 판단하고, 금액은 KRW 정수로 보관한다. 방향은 출금 `TRANSFER_OUT`, 반환 `RETURN_IN`처럼 명시하며, 방향이 없는 분석 언급은 거래 행으로 만들지 않고 `미확인` 정황으로 남긴다.

`actions`는 이미 실행했거나 진행 중인 조치 기록, `case_tasks`는 앞으로 해야 할 업무이므로 둘은 유지하고 서로 덮어쓰지 않는다.

`case_context_projections.last_success_payload`는 캐시다. 원본 사실이나 직원 편집 이력이 아니므로 다음 정책을 확정한 뒤에만 보존 기간을 줄인다.

- TTL과 최대 보존 기간
- 만료·손상 시 canonical 원장에서 재생성하는 절차
- 캐시 삭제 후 Context Panel 복구 테스트
- 캐시 삭제가 `case_context_items`와 history를 건드리지 않는지 확인
- 생성 실패 시 마지막 성공 payload를 보여줄지 여부
- 오래된 행 정리 방식과 모니터링

### Fact route·저장소 초기 조사 결과

현재 V2가 저장·조회 원본이다. `/facts` 경로는 구버전 응답 모양을 위한 adapter로만 유지하며, 프론트엔드는 Context V2 workspace를 사용한다.

| 호출/경로 | 현재 코드 위치 | 저장소·테이블 | 현재 책임 | 판정 |
|---|---|---|---|---|
| 구버전 Fact 조회 | 외부 구버전 클라이언트만 | `GET /api/cases/{case_id}/facts` → `repository.list_case_facts` → V2 adapter | 기존 응답 모양 유지 | 호환 adapter |
| Context V2 리소스/검토 | `frontend/src/context-v3/api.ts`, `ContextWorkspace.tsx` | `/context-v2/resources`, `/context-v2/facts*` → `case_context_facts_v2` | 근거·상태·확정자·버전이 있는 canonical 후보 | V2 직접 사용 중 |
| Context V2 workspace | `backend/general_api/app/main.py`의 `read_context_workspace` | `case_context_facts_v2` | V2 항목만 반환 | canonical |
| AI 지원·질문 추천 | `backend/general_api/app/main.py`의 `_read_case_support_source`, 질문 계획 경로 | legacy Fact를 읽고 V2 resources를 `merge_support_records`로 병합 | 기존 AI 입력과 최신 Context를 함께 구성 | 두 모델 병합 |
| MySQL legacy write | `backend/general_api/app/domains/cases/mysql_repository.py` | `INSERT/SELECT/UPDATE case_context_facts_v2` | 고객 답변·질문 Fact 후보 | V2 전환 완료 |
| MySQL V2 write/review | `backend/general_api/app/domains/cases/case_context_v2_repository.py` | `INSERT/UPDATE case_context_facts_v2` | 제안·확정·기각·대체와 이력 | 기준 원장 |

현재 결론은 **V2가 유일한 canonical source**다. `/facts`는 삭제 전까지 V2를 legacy 응답으로 변환한다.

#### 마이그레이션 전 데이터 비교 결과 — 2026-09-22 01:44 UTC 읽기 전용 snapshot

- `case_facts`: 물리 테이블 DROP 완료(027 복사·028 정리 후).
- `case_context_facts_v2`: 264행, 기존 258행 + legacy 6행의 deterministic ID 복사, 17개 Case에 분포.
- legacy 필드 구성: `authentication_information_exposure` 3행, `personal_information_exposure` 3행.
- 의미 키 대응 결과: `exposure.authentication_information`은 `VP-1` 1행, `VP-14` 1행, `VP-15` 4행을 포함하고, `exposure.personal_information`은 세 Case 각각 1행이다.
- legacy `AI_EXTRACTED`는 V2의 `AI_EXTRACTION` 후보로 매핑할 수 있지만, legacy confidence `0.7000`과 V2의 일부 `NULL/0.9500` 값은 동일하지 않다.
- 비식별 SHA-256 비교에서도 대응 semantic key의 legacy `value`와 V2 `display_value`가 바이트 단위로 일치한 행은 확인되지 않았다. 표시 형식 차이 가능성은 남아 있으므로 현재 6행을 자동 병합하지 않는다.
- 따라서 legacy 6행은 V2에 **의미상 대응하는 행이 이미 존재할 가능성이 높지만**, 근거·값·source가 같은 동일 행으로 확정할 수 없다. V2의 같은 semantic key가 여러 행인 것은 여러 정황을 보존한 결과일 수 있으므로 중복으로 단정하지 않는다.

#### 중복·충돌 처리 규칙

1. **완전 동일**: Case, semantic key, 정규화 값, 근거 집합, source, status가 모두 같으면 하나의 V2 행으로 병합한다.
2. **근거만 다름**: 각각 별도 Fact로 보존한다. 근거가 다른 발화를 하나로 합치지 않는다.
3. **값이 다름**: 둘 다 `PROPOSED`로 보존하고 직원 검토 대상으로 둔다. 자동으로 최신 값이나 더 강한 표현을 선택하지 않는다.
4. **상태가 다름**: `CONFIRMED`는 확인자·확정 시각이 있는 경우에만 우선한다. 기존 확정 Fact를 덮어쓰지 않고 새 Fact와 `SUPERSEDED` 관계를 남긴다.
5. **source가 다름**: `CUSTOMER_STATEMENT`, `AI_EXTRACTION`, `STAFF_OBSERVATION`, `BANK_RECORD`, `OFFICIAL_VERIFICATION`을 구분한다. AI 추출을 직원 확인이나 은행 기록으로 승격하지 않는다.
6. **매핑 불가**: semantic key·source·status가 허용 목록에 없으면 migration을 중단하거나 별도 quarantine 목록에 기록한다. 임의의 `UNKNOWN` 변환으로 통과시키지 않는다.
7. **재실행 안전성**: `legacy:<fact_id>` 또는 별도 `client_request_id`를 사용해 migration 재실행 시 중복 행이 생성되지 않게 한다.

#### V2 복사 migration 실행 결과 — 2026-09-22 02:18 UTC

- `027_migrate_legacy_case_facts_to_v2.sql` 적용 완료: legacy 지원 6행을 deterministic `legacy-<sha256>` ID와 `legacy-case-fact:<fact_id>` 요청 키로 V2에 복사했다.
- `028_retire_legacy_case_facts.sql` 적용 완료: legacy 행 0건 확인 후 유지보수 창에서 `case_facts` 물리 테이블 DROP 완료.
- 신규 MySQL 고객 답변·Fact 제안·확정 저장은 모두 `case_context_facts_v2`를 사용한다. 프론트 Case Room도 `/facts` 대신 Context V2 workspace를 읽는다.
- V2와 legacy 응답을 합칠 때 동일 `fact_id`는 중복 제거하고, V2의 확정 값은 legacy 후보가 덮어쓰지 않는다.

이 규칙으로 dry-run 비교를 거쳐 신규 write를 V2로 고정했고, `/facts`는 V2 adapter로 전환했다. `case_facts` 물리 테이블은 DROP했으므로 이제 호환 API는 V2 adapter만 사용한다.

## 테이블별 사용처 판정

행 수는 `DB_CATALOG.md` 스냅샷이다. 0행은 미사용 확정이 아니라 “현재 데모에서 아직 생성되지 않음”을 뜻한다.

| 테이블 | 행 수 | 분류 | 실제 사용처 | 이번 단계 판정 |
|---|---:|---|---|---|
| `cases` | 17 | 핵심 원장 | Case 생성/조회/수정/휴지통/복구, bundle·보고서 기준 | 유지 |
| `case_inputs` | 17 | 핵심 원장 | 분석 입력 저장, 최초 분석 결과의 일회성 원문 확인 | 유지. `input_text`는 일반 read/list/bundle과 지원 AI에 반환 금지 |
| `analysis_segments` | 94 | 활성 projection | 분석 결과 정황 구간·위험도 | 유지 |
| `context_features` | 2,584 | 활성 projection | 위험도/분석 feature 저장 및 Context 계산 | 유지. 고카디널리티 정리 후보는 후속 |
| `case_semantic_atoms` | 129 | 핵심 projection | 역할·행동·금액·시간 semantic 상세 표시 | 유지 |
| `case_semantic_relations` | 16 | 핵심 projection | Atom 간 순서·인과·연결 관계 | 유지 |
| `case_context_signals` | 0 | 활성 projection | 구조화 signal 투영 계약 | 유지. 빈 행만으로 제거하지 않음 |
| `bank_staff_directory` | 12 | 핵심 원장 | 직원 목록·직무·배정 가능 여부 | 유지 |
| `case_members` | 26 | 핵심 원장 | 담당자 배정/수정/권한/역할 | 유지 |
| `case_presence` | 21 | 활성 상태 | Case 접속 상태·heartbeat | 유지 |
| `messages` | 199 | 핵심 원장 | 은행/고객/AI 대화·시스템 이벤트 | 유지 |
| `customer_questions` | 20 | 핵심 원장 | 질문 후보·고객 질문·답변 상태 | 유지 |
| `message_context_extractions` | 139 | 활성 projection | 메시지에서 Fact 후보를 추출한 상태·재시도 | 유지 |
| `case_transactions` | 0 | 선택 기능 | 데모 송금 기록 조회/등록/수정 API와 `송금 기록 조회` 카드 | 유지. 실제 은행 원장으로 표시하지 않으며 0건을 피해금액 0원으로 해석하지 않음 |
| `case_facts` | — | 제거 완료 | 027/028 이후 물리 테이블 없음. `/facts`는 V2 adapter | 완료 |
| `case_context_facts_v2` | 264 | 핵심 원장 | proposed/confirmed/rejected/superseded Fact | 유지 |
| `case_gaps` | 0 | 선택 기능 | 미확인 사항·해소 근거 | 유지. Context V2 API가 제공 |
| `verification_tasks` | 0 | 선택 기능 | 별도 확인 업무와 고객 공개 결과 | 유지 |
| `case_context_observations` | 0 | 선택 기능 | 표준 분류 밖 관찰 | 유지. 누락 방지용 |
| `actions` | 76 | 핵심 원장 | 조치 저널·고객 진행 상태·실제 업무 기록 | 유지 |
| `case_ai_suggestions` | 0 | 선택 기능 | AI 업무 제안과 사람 검토 상태 | 유지 |
| `case_tasks` | 0 | 선택 기능 | 담당자 업무 진행/완료/차단 | 유지 |
| `case_decisions` | 0 | 선택 기능 | 직원 판단·결정 이력 | 유지 |
| `case_context_items` | 0 | 선택 기능 | 직원용 표시 편집본 | 유지 |
| `case_context_projections` | 17 | 활성 캐시/lease | Context 생성 lease, revision, 마지막 성공 payload | 유지. TTL/재생성 정책은 후속 |
| `personal_notes` | 0 | 선택 기능 | 직원 개인 메모 | 유지 |
| `case_reports` | 17 | 핵심 projection | LIVE/FINAL 보고서 원장; `live_report`는 초기 분석 snapshot이고 우측 Context Panel 공개 계약과 분리 | 유지 |
| `case_report_sections` | 119 | 핵심 projection | 보고서 섹션별 JSON/version | 유지 |
| `case_events` | 351 | 감사 원장 | 담당자·Fact·업무 변경 타임라인 | 유지, append-only 원칙 |
| `case_context_item_history` | 0 | 감사 이력 | 직원 표시 편집 변경 이력 | 유지 |
| `case_context_v2_history` | 258 | 감사 이력 | V2 자원 변경 이력 | 유지 |
| `voice_sessions` | 0 | 호환/metadata | 세션 상태·참여자와 Case bundle의 음성 상태 | 유지. 원문 segment는 저장하지 않음 |
| `schema_migrations` | 30 | 스키마 운영 | 적용 migration 기준선 | 유지, 수동 삭제 금지 |

## 컬럼별 중복·무결성 검토

`DB_CATALOG.md`가 356개 컬럼의 타입·NULL·PK/FK·인덱스를 원본 표로 제공한다. 아래는 삭제/통합 판단에 직접 영향을 주는 컬럼군이다. ID·created_at·updated_at·version·status는 여러 테이블에 반복되지만 각 원장/동시성/감사 책임이 달라 중복 컬럼으로 보지 않는다.

| 컬럼군 | 현재 역할 | 위험/중복 | 판정 |
|---|---|---|---|
| `cases.diagnosis_json`, `initial_brief` | 분석 결과와 Case 초기 요약 | semantic/segment/report projection과 내용이 겹칠 수 있음 | 유지. canonical source 결정 전 삭제 금지 |
| `cases.victim_transfer_status`, `actual_loss_amount_krw` | Case 단일 요약 상태·피해금액 | `case_transactions` 여러 건과 혼동 가능 | 유지. 다중 거래 원장으로 사용하지 않도록 API/문서 고정 |
| `case_inputs.input_type`, `input_text` | 입력 유형·데모 원문 | 원문 재전달/무기한 보관 위험 | 유지. 지원 AI payload 차단과 보존 기간을 별도 운영 규칙으로 관리 |
| `analysis_segments.segment_text`, `evidence_json` | 원문이 아닌 정황 라벨·근거 metadata | 원문 phrase가 다시 들어가면 privacy 경계 위반 | 유지. 원문 문장 저장 금지 검증 필요 |
| `context_features.feature_key/value/source` | 수치 feature | 같은 의미가 JSON/payload에도 중복될 수 있고 행 수가 빠르게 증가 | 유지. key allowlist·압축/retention은 후속 |
| `case_semantic_atoms/relations.payload_json` | 상세 semantic payload·관계 | `diagnosis_json`과 부분 중복 | 유지. 화면 누락 방지용 canonical 상세로 사용 |
| `messages.content` | Case 채팅 원문 | `case_inputs` 원문과 혼동 위험 | 유지. 채팅 원문과 통화 입력 원문은 별도 책임 |
| `case_facts.*` | 구 Fact 모델 | V2 Fact와 모델 중복 | 제거 완료. V2만 유지 |
| `case_context_facts_v2.value_json`, `source_*`, `status` | Fact 값·근거·확정 상태 | report/context JSON에 projection됨 | 유지. V2 원장을 우선하고 projection은 재생성 가능하게 유지 |
| `case_gaps`, `verification_tasks`의 상태/결과 | 미확인·확인 업무 | 0행이라 기능이 없어 보일 수 있음 | 유지. 질문·검증 UI와 연결됨 |
| `actions`와 `case_tasks` | 실제 조치 기록 vs 담당자 업무 | 이름이 모두 업무처럼 보여 중복 오해 | 둘 다 유지. Action=실제 조치/진행 기록, Task=할 일/상태 |
| `case_ai_suggestions`와 `case_decisions` | AI 제안 vs 직원 판단 | 같은 사건 결론을 중복 기록할 수 있음 | 유지. human-in-control 이력 보존을 위해 분리 |
| `case_context_items`와 `case_context_item_history` | 현재 직원 표시 편집본 vs 변경 이력 | 현재값과 이력이 중복되어 보임 | 유지. 이력 삭제 금지 |
| `case_context_projections.last_success_payload` | 재생성 비용을 줄이는 캐시 | `cases.diagnosis_json`/report와 중복 | 유지. 캐시 만료·재생성 가능성만 후속 설계 |
| `case_reports`와 `case_report_sections` | 보고서 원장 vs 섹션 단위 version | 전체 JSON과 섹션 JSON의 중복 가능 | 유지. FINAL 보고서 감사/부분 갱신 때문에 분리 |
| `case_events.payload_json` | append-only 이벤트 상세 | 현재 상태 컬럼과 중복될 수 있음 | 유지. 현재 상태의 source로 역사용하지 않음 |
| `voice_sessions.participants_json` | 세션 참여자 metadata | 원문을 담을 수 있는 확장 위험 | 유지. transcript 필드/하위 테이블 금지 |

## API·기능 제거/전환 결과

### 제거·전환한 경로

- `case_facts` 신규 저장·조회 경로를 제거했다. 고객 답변·질문 Fact와 Case 지원 입력은 V2만 사용한다.
- `GET/POST /api/cases/{case_id}/facts`는 당분간 V2 행을 legacy 응답으로 변환하는 호환 adapter다. 프론트엔드에서는 더 이상 호출하지 않는다.

- `POST/GET /api/cases/{case_id}/voice-sessions/{session_id}/transcript`
  - 요청 body를 파싱하지 않고 `410 TRANSCRIPT_STORAGE_DISABLED` 반환
  - repository의 transcript append/list 경로 제거
  - `transcript_segments` migration은 테이블이 비어 있을 때만 DROP하고, 행이 있으면 fail-closed로 중단
  - 분석 API가 받은 데모 원문은 `case_inputs`에만 기록하고, 최초 분석 결과 화면의 transient 입력 외 API 응답·지원 AI 요청 DTO에는 포함하지 않음

### 유지하되 책임을 좁힌 경로

- `POST/PATCH /api/cases/{case_id}/voice-sessions`는 세션 상태·참여자 metadata만 다룬다. Frontend의 현재 핵심 흐름에는 직접 호출처가 없지만 Case bundle 호환을 위해 유지한다.
- `case_facts` API는 외부 구버전 클라이언트 호환을 위해 잠시 유지한다. 저장소는 V2만 사용하며, 물리 테이블은 이미 DROP되어 legacy API는 V2 adapter로만 동작한다.

## 이번 단계에서 하지 않은 작업

- 데이터 백업/export
- 행 데이터 이동·정합성 보정
- `case_facts` 물리 DROP(완료)
- `case_facts`·diagnosis/report projection 통합
- 전체 회귀 테스트 재실행

위 항목은 사용처 분류 결과를 기준으로 별도 PR에서 진행한다. 삭제 migration은 반드시 metadata/row 백업, dry-run, FK·API 회귀, rollback 가능성을 갖춘 뒤 실행한다.

## 다음 단계 입력값

1. ~~`case_facts`와 `case_context_facts_v2`의 route별 read/write 목록을 고정한다.~~ 완료. 이후 `/facts`는 V2 adapter만 유지한다.
2. `cases.diagnosis_json`·semantic tables·reports 사이의 authoritative field matrix를 작성한다.
3. 0행 선택 기능은 화면/API 호출 telemetry 또는 명시적 제품 결정으로만 deprecate한다.
4. 원문(`case_inputs.input_text`)의 데모 보관 기간과 export 권한을 정한 뒤 보존/삭제 migration을 별도 검토한다.
5. 프론트엔드 타입·백엔드 공개 계약·repository SQL의 의미 불일치는 [API_CONTRACT_AUDIT.md](API_CONTRACT_AUDIT.md)에서 먼저 결정한다. 특히 `case_members.role`/`assignment_role`, `CaseBundle` 호환 필드, 금액 표현을 DB 삭제보다 앞서 확정한다.
6. 우측 Context Panel은 DB 정리보다 후순위다. UI/UX·표시 항목·상태를 먼저 정하고, `live_report` JSON에 직접 결합하지 않는 표시용 계약과 mock 프론트를 만든 뒤 API·DB 변경 여부를 결정한다.

## DB 정리 후속 TODO·체크리스트

아래 항목은 전부 반드시 삭제해야 하는 목록이 아니다. **무결성·원문 접근 경계에 필요한 항목은 필수**, 중복 축소·성능 개선 항목은 제품 범위를 확정했을 때 선택적으로 진행한다. 체크하지 않은 항목은 구현된 것으로 간주하지 않는다.

### 0단계 — 현재 기준선 고정 (완료)

- [x] `DB_CATALOG.md` 생성: 테이블·컬럼·PK/FK·인덱스·행 수 기록
- [x] REST route·repository SQL·Frontend 호출처별 사용처 분류
- [x] FK 위반·Case orphan·migration 누락을 읽기 전용으로 점검
- [x] `transcript_segments`가 비어 있을 때만 삭제하는 fail-closed migration 추가
- [x] 레거시 transcript GET/POST를 `410 TRANSCRIPT_STORAGE_DISABLED`로 전환
- [x] 분석 원문 저장 위치를 `case_inputs.input_text` 하나로 고정
- [x] Case read/list/bundle API와 Case Room에서 원문을 반환하지 않고, 최초 분석 결과 화면의 transient 입력만 표시하도록 고정

### 1단계 — canonical source 확정 (필수)

#### `case_facts` → `case_context_facts_v2`

- [x] route별 read/write 목록 작성: `/facts`, 질문 답변, Context V2, AI extraction
- [x] 동일 Case·Fact의 legacy/V2 대응 키와 상태(PROPOSED/CONFIRMED/REJECTED/SUPERSEDED) 비교
- [x] `field_name`·`source`·`evidence_message_id`·`source_question_id`의 V2 매핑 allowlist 승인
- [x] 값·근거·source·status를 원문 노출 없이 hash/metadata 기반 dry-run 비교
- [x] 완전 동일·근거 차이·값 충돌·상태 충돌을 분리한 migration 보고서 작성
- [x] `legacy:<fact_id>` 또는 `client_request_id` 기반 재실행 중복 방지 확인
- [x] V2 read를 기본으로 전환하고 legacy read는 V2 adapter로 제한
- [x] 신규 write를 V2로만 보내고 legacy 저장 경로를 제거
- [x] legacy 행 검증·정리 및 deprecation 전환
- [x] **완료 조건:** 모든 화면/AI가 V2를 기준으로 읽고, legacy 테이블 행이 0건이며 물리 테이블이 제거됨

#### `cases.diagnosis_json` ↔ semantic/projection/report

- [ ] 필드별 authoritative source matrix 작성
- [ ] `case_semantic_atoms`, `case_semantic_relations`, `analysis_segments`와 diagnosis의 동일 필드 비교
- [ ] report와 Context projection이 원장 재생성으로 복원되는지 확인
- [ ] 중복 JSON을 삭제하지 않고 먼저 read model/cache로 명시
- [ ] **완료 조건:** 한 필드에 원본이 두 개 존재하지 않고, projection 재생성 테스트가 통과

### 2단계 — 선택 기능 유지/제거 결정 (제품 결정 필요)

#### 거래·금액 (데모 정책)

- [x] 실제 은행 확인 거래 원장은 연동하지 않고, `case_transactions`는 분석·채팅·직원 입력 기반 데모 표시 목록으로 사용
- [x] `cases.actual_loss_amount_krw`는 단일 요약값으로 유지하고 자동 합산·자동 승격하지 않음
- [x] 요구 금액·송금 진술·직원 데모 확인 기록을 `case_context_facts_v2`/`case_transactions`로 구분
- [x] 데모 기록의 중복 식별키와 방향(`TRANSFER_OUT`/`RETURN_IN` 등)을 정의
- [x] 금액은 KRW 정수로 표현하고 출처·확인 상태·통화 단위를 기록
- [ ] `actual_loss_amount_krw` 요약값과 `case_transactions` 거래 목록의 합산·자동 승격 금지 회귀 테스트
- [ ] **완료 조건:** `송금 기록 조회` 카드가 “거래 없음/조회 실패/미확인/송금 진술/데모 확인”을 구분하고 금액 합계 회귀가 통과

#### 업무·AI 제안

- [ ] `actions`(실제 조치 기록)와 `case_tasks`(해야 할 일)의 UI/API 책임을 문서화
- [ ] `case_ai_suggestions` → `case_tasks` 전환·채택 상태 확인
- [ ] `case_decisions`에 직원 판단과 확인자를 남기는지 확인
- [ ] 실제 사용하지 않는 제안/업무 화면이 있으면 route deprecation 여부 결정
- [ ] **완료 조건:** Action과 Task가 서로 덮어쓰지 않고 타임라인·Context Panel에서 중복 표시되지 않음

#### Context 편집·캐시

- [ ] `case_context_items`와 `case_context_item_history`의 현재값/이력 책임 확인
- [ ] `case_context_projections.last_success_payload`의 TTL과 재생성 절차 정의
- [ ] 캐시를 삭제해도 원장으로 Context Panel을 복원하는지 확인
- [ ] **완료 조건:** 캐시 삭제 후 재생성 성공, 직원 편집 이력 보존

#### 첨부·음성 호환

- [x] 데모에서 첨부파일 기능을 제외하기로 결정
- [x] Frontend 버튼·route·repository를 제거/410 전환
- [x] 빈 테이블 확인 후 `attachments/026_retire_attachments.sql` 적용
- [ ] `voice_sessions` 외부 소비자와 Case bundle 사용처 확인
- [ ] 외부 소비자가 없을 때만 metadata API 및 테이블 제거 계획 수립
- [ ] **완료 조건:** 제거 대상 API 호출처 0건, 기존 데이터 export 완료, 호환 응답 또는 410 계약 존재

#### `messages.attachments_json` 최종 정리 순서

이 컬럼은 첨부파일 기능을 다시 켜기 위한 것이 아니라, 구버전 응답 계약을 깨지 않기 위한 빈 compatibility shim이다. 핫픽스가 안정화된 뒤 아래 순서로 가장 마지막에 검토한다.

- [ ] 구버전 웹·모바일·스크립트가 `attachments`, `attachment_ids`, `attachments_json`을 읽거나 보내지 않는지 저장소·배포 목록·접근 로그로 확인
- [ ] 모든 메시지 행의 `attachments_json`이 `NULL` 또는 빈 배열인지 읽기 전용 점검
- [ ] 새 클라이언트와 API 계약 테스트에서 첨부 필드 제거 후에도 채팅·AI 응답이 정상인지 확인
- [ ] 컬럼 제거 migration과 410 첨부 API 계약을 함께 리뷰
- [ ] 백업·복원·DB catalog diff·Backend/Frontend 회귀 테스트 통과
- [ ] **완료 조건:** 외부 소비자 0건, 실제 첨부 데이터 0건, 새 계약 배포 완료 후에만 컬럼 DROP

### 3단계 — 데이터 보존·백업 (삭제 전 필수)

- [ ] 서비스 DB 읽기 중지 창과 담당자 공지
- [ ] 전체 schema + 업무 행 백업 생성
- [ ] `case_inputs.input_text`, messages, notes, attachments metadata의 접근권한과 보관 위치 확인
- [ ] 별도 빈 DB 복원 리허설
- [ ] FK·행 수·Case별 checksum·핵심 API 응답 비교
- [ ] 백업 receipt와 SHA-256을 Git 제외 경로에 보관
- [ ] **완료 조건:** 복원 DB에서 핵심 Case/담당자/채팅/Context가 동일하게 조회됨

### 4단계 — 삭제 migration·회귀 (마지막 단계)

- [ ] 삭제 대상 테이블/컬럼과 영향 route를 migration 파일에 명시
- [ ] DROP 전 행 수가 0인지 또는 보존 export가 완료됐는지 fail-closed 검사
- [ ] FK·trigger·index 제거 순서와 rollback/forward-only 정책 검토
- [ ] API 계약 테스트: 2xx/404/409/410 응답과 원문 비노출
- [ ] Backend repository·General API 회귀
- [ ] Frontend typecheck·Vite build·브라우저 E2E
- [ ] Case 생성→최초 원문 확인→Case Room 재진입에서 원문 비노출 확인
- [ ] 담당자 배정·채팅·AI 지원·거래 카드·보고서 회귀
- [ ] **완료 조건:** 전체 Required Check 통과 및 삭제 전/후 DB catalog diff 승인

### 문서 최신화 기준

- `DB_CATALOG.md`는 `inspect_database.py`와 `export_database_catalog.py`로 실제 information_schema·행 수를 다시 읽어 갱신한다.
- `DB_USAGE_AUDIT.md`의 체크박스는 실제 완료된 검증만 `[x]`로 표시한다. 계획·검토 대상은 `[ ]`로 둔다.
- migration 폴더 변경 시 `backend/migrations/README.md`, `manifest.json`, `database/README.md`의 엔티티 목록과 실행 절차를 함께 대조한다.
