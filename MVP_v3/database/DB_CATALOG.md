# 전체 DB 구조·현재 상태 표

기준 DB: `csr` · 조회 시각(UTC): `2026-09-22T06:23:10.311303+00:00`

> 실제 information_schema와 COUNT(*)로 생성한 시점별 스냅샷이다. 개인정보·대화·계좌 값은 포함하지 않는다. 0건은 테이블 누락이 아니라 비어 있는 상태다.

| 검사 | 결과 |
|---|---|
| 테이블 / 컬럼 | 32개 / 356개 |
| 트리거 / 선언된 FK | 26개 / 35개 |
| FK 위반 / Case 연결 누락 | 0종 / 0종 |
| 현재 migration 중 미기록 | 0개 |
| 현재 파일 없는 과거 적용 기록 | 021_bank_staff_assignment_fields.sql |

과거 `021_bank_staff_assignment_fields.sql` 기록은 삭제/재작성하지 않는다. 현재 직원 구조는 020·024와 대조한다. `case_number_sequences`는 allocator 변경이 되돌려진 현재 코드에서 사용하지 않으므로 없는 것이 정상이다.
첨부파일 기능은 데모 범위에서 제외되어 `case_attachments`·`message_attachments` 테이블이 존재하지 않는 것이 정상이다. `messages.attachments_json`은 구버전 계약 호환을 위해 현재 빈 값만 유지하며, 핫픽스 안정화 후 마지막 계약 변경에서 제거 여부를 재검토한다.

## 읽는 방법

- [엔티티별 마이그레이션](../backend/migrations/README.md) · [사용처·정리 감사](DB_USAGE_AUDIT.md) · [API 계약 대조](API_CONTRACT_AUDIT.md) · [운영/백업/재생성](README.md) · [확인된 데이터·금액 후속 문제](../docs/CURRENT_STATUS.md)
- 업무 정황 Fact, 은행 확인 거래, 직원 편집본, 캐시는 서로 다른 책임이다. 같은 내용이 여러 테이블에 보인다고 즉시 삭제하지 않는다.
- 거래 0건을 피해금액 0원으로 해석하지 않는다. NULL은 미등록/미확인이다. PROPOSED는 확인 전 후보다.

## 엔티티별 전체 테이블

| 엔티티 | 테이블 | 역할 | 행 수 | 기본 키 | 물리 FK 대상 |
|---|---|---|---:|---|---|
| 사건·분석 | [`cases`](#table-cases) | 사건 원장·요약·상태·구조화 분석 JSON | 17 | case_id | — |
| 사건·분석 | [`case_inputs`](#table-case_inputs) | 데모 입력 원문과 입력 유형을 보관하는 Case 입력 원장; 최초 분석 결과 화면에서만 일시 확인하고 일반 Case read/list/bundle·지원 AI에는 반환하지 않음 | 17 | input_id | cases |
| 사건·분석 | [`analysis_segments`](#table-analysis_segments) | 원문이 아닌 정황 라벨·구간 위험도 | 94 | segment_id | cases |
| 사건·분석 | [`context_features`](#table-context_features) | 정규화된 수치 피처 | 2584 | feature_id | analysis_segments, cases |
| 사건·분석 | [`case_semantic_atoms`](#table-case_semantic_atoms) | 역할·행동·금액·시간을 보존하는 의미 단위 | 129 | case_id, atom_id | cases |
| 사건·분석 | [`case_semantic_relations`](#table-case_semantic_relations) | 의미 단위 간 순서·인과 등의 관계 | 16 | case_id, relation_id | cases |
| 사건·분석 | [`case_context_signals`](#table-case_context_signals) | 구조화 신호 투영 | 0 | case_id, signal_id | cases |
| 직원·참여자 | [`bank_staff_directory`](#table-bank_staff_directory) | 등록 은행 직원과 배정 가능 직무 | 12 | staff_id | — |
| 직원·참여자 | [`case_members`](#table-case_members) | Case별 참여자·시스템 권한·배정 역할·제거 상태 | 26 | case_id, user_id | cases |
| 직원·참여자 | [`case_presence`](#table-case_presence) | 사용자 접속·만료 시각; 담당자 배정과 별개 | 22 | case_id, user_id | cases |
| 대화·고객 질문 | [`messages`](#table-messages) | 고객/은행/AI 대화와 시스템 이벤트; 통화 입력 원문과 별개; attachments_json은 현재 빈 호환 필드 | 202 | message_id | cases |
| 대화·고객 질문 | [`customer_questions`](#table-customer_questions) | 고객 질문·선택지·답변·질문 버전 | 20 | question_id | cases |
| 대화·고객 질문 | [`message_context_extractions`](#table-message_context_extractions) | 메시지→사실 후보 추출 작업·재시도 상태 | 142 | extraction_id | cases, messages |
| 금액·거래 | [`case_transactions`](#table-case_transactions) | 외부 은행 원장이 아닌 Case 내부 확인 거래 기록; Context V2 실제 금액 사실을 직원 확인 후 승격 | 0 | id | cases |
| 사실·확인 | [`case_context_facts_v2`](#table-case_context_facts_v2) | AI·대화·직원 확인에서 나온 사실 후보·확정·기각·대체 상태와 근거; 거래 승격 전의 기준 원장 | 264 | fact_id | case_context_facts_v2, cases |
| 사실·확인 | [`case_gaps`](#table-case_gaps) | 미확인 사항과 해소 근거 | 0 | gap_id | case_context_facts_v2, cases |
| 사실·확인 | [`verification_tasks`](#table-verification_tasks) | 별도 확인 업무·결과·공개 여부 | 0 | verification_task_id | cases |
| 사실·확인 | [`case_context_observations`](#table-case_context_observations) | 표준 분류에 매핑되지 않은 구조화 관찰 | 0 | case_id, observation_id | cases |
| 조치·업무·결정 | [`actions`](#table-actions) | 기존 조치 저널·고객 진행 상태 등; 실제 외부 실행 증거와 구분 | 157 | action_id | cases |
| 조치·업무·결정 | [`case_ai_suggestions`](#table-case_ai_suggestions) | AI 업무 제안·검토·채택 상태 | 0 | suggestion_id | cases |
| 조치·업무·결정 | [`case_tasks`](#table-case_tasks) | 담당자 업무·진행·완료·차단 상태 | 0 | task_id | case_ai_suggestions, cases |
| 조치·업무·결정 | [`case_decisions`](#table-case_decisions) | 직원 판단·결정 기록 | 0 | decision_id | case_decisions, cases |
| 화면·캐시 | [`case_context_items`](#table-case_context_items) | 직원 표시 편집본과 버전; 원본 사실과 별개 | 0 | item_id | cases |
| 화면·캐시 | [`case_context_projections`](#table-case_context_projections) | 맥락 생성 lease·revision·마지막 성공 결과 캐시; 원본 사실·직원 이력과 별개 | 17 | case_id | cases |
| 화면·캐시 | [`personal_notes`](#table-personal_notes) | 작성자 개인 메모 | 0 | note_id | cases |
| 보고서·이력 | [`case_reports`](#table-case_reports) | LIVE/FINAL 보고서 원장; live_report는 초기 분석 snapshot이며 우측 Context Panel의 공개 계약과 분리 | 17 | report_id | cases |
| 보고서·이력 | [`case_report_sections`](#table-case_report_sections) | 보고서 섹션 JSON·버전 | 119 | report_id, section_key | case_reports |
| 보고서·이력 | [`case_events`](#table-case_events) | Case 업무 이벤트 타임라인 | 435 | event_id | cases |
| 보고서·이력 | [`case_context_item_history`](#table-case_context_item_history) | 직원 표시 편집 변경 이력 | 0 | history_id | case_context_items |
| 보고서·이력 | [`case_context_v2_history`](#table-case_context_v2_history) | 사실·업무 등 V2 자원 변경 이력 | 258 | history_id | cases |
| 음성·호환 | [`voice_sessions`](#table-voice_sessions) | 음성 세션 상태·참여자 metadata; 원문 segment 저장 없음; API·bundle 호환용 | 0 | session_id | cases |
| 스키마 운영 | [`schema_migrations`](#table-schema_migrations) | 적용 또는 검증된 기준선의 전체 migration 파일명 | 31 | migration_name | — |

## 금액 저장 위치 구분

| 위치 | 의미 | 합산 시 주의 |
|---|---|---|
| `cases.actual_loss_amount_krw` | 사건별 단일 요약 피해금액 | 다중 송금 목록이 아님. 현재 자동 동기화 없음 |
| `case_transactions.amount` | 직원 확인 후 등록된 Case 내부 개별 거래 | 외부 금융기관 연동값이 아님. 요구·약속·PROPOSED 사실은 자동 승격하지 않음 |
| `case_context_facts_v2.value_json.amount_krw` | 요구/진술/확인 정보 | PROPOSED를 확정 거래 합계에 포함하지 않음 |
| `case_semantic_atoms.payload_json.amount_value_krw` | 분석 정황의 금액 언급 | 반복 언급·예정·요구를 별도 거래로 간주하지 않음 |
| `cases.diagnosis_json` / projection JSON | 분석·화면·AI 입력용 복제/캐시 | 원장과 중복 합산하지 않음 |

## 테이블별 전체 컬럼·인덱스·제약조건

<a id="table-cases"></a>

### cases

사건·분석 — 사건 원장·요약·상태·구조화 분석 JSON

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 17행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `case_id` | varchar(32) | NO | — | PRIMARY | 사건 연결 키 |
| `case_name` | varchar(200) | YES | — |  | — |
| `client_request_id` | varchar(100) | YES | — | client_request_id | 재요청 중복 방지 키 |
| `risk_level` | enum('NORMAL','LOW','HIGH') | NO | — |  | — |
| `risk_score` | decimal(9,6) | NO | — |  | — |
| `mode` | enum('PREVENT','RECOVERY','CLOSED') | NO | PREVENT |  | — |
| `status` | enum('NEW','TRIAGE','VERIFYING','IN_PROGRESS','CLOSED') | NO | TRIAGE |  | 자원별 처리 상태 |
| `version` | int | NO | 1 |  | 낙관적 잠금/수정 버전 |
| `context_revision` | bigint | NO | 1 |  | 의미 데이터 변경 revision |
| `initial_brief` | text | NO | — |  | — |
| `diagnosis_json` | json | NO | — |  | 원문 제거된 분석 결과와 정황 metadata |
| `created_at` | datetime(6) | NO | — |  | 생성 시각 |
| `updated_at` | datetime(6) | NO | — |  | 최종 갱신 시각 |
| `victim_transfer_status` | varchar(30) | YES | — |  | Case 수준의 송금 여부; 개별 거래 완료 상태와 구분 |
| `actual_loss_amount_krw` | bigint | YES | — |  | 단일 요약 피해금액(KRW); 개별 송금 목록/자동 합계 아님 |
| `deleted_at` | datetime(6) | YES | — |  | 논리 삭제 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `client_request_id` | 예 | client_request_id |
| `PRIMARY` | 예 | case_id |

| FK / CHECK | 정의 |
|---|---|
| — | 없음 |

<a id="table-case_inputs"></a>

### case_inputs

사건·분석 — 데모 입력 원문과 입력 유형을 보관하는 Case 입력 원장; 최초 분석 결과 화면에서만 일시 확인하고 일반 Case read/list/bundle·지원 AI에는 반환하지 않음

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 17행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `input_id` | bigint | NO | — | PRIMARY / auto_increment | — |
| `case_id` | varchar(32) | NO | — | fk_case_inputs_case | 사건 연결 키 |
| `input_type` | enum('TEXT','VOICE_TRANSCRIPT') | NO | TEXT |  | — |
| `input_text` | text | NO | — |  | 데모 입력 원문; 최초 분석 결과 화면에서만 일시 확인하며 일반 Case read/list/bundle·지원 AI 입력에는 포함하지 않음 |
| `created_at` | datetime(6) | NO | — |  | 생성 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `fk_case_inputs_case` | 아니오 | case_id |
| `PRIMARY` | 예 | input_id |

| FK / CHECK | 정의 |
|---|---|
| `fk_case_inputs_case` | case_id → cases.case_id; DELETE NO ACTION; UPDATE NO ACTION |

<a id="table-analysis_segments"></a>

### analysis_segments

사건·분석 — 원문이 아닌 정황 라벨·구간 위험도

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 94행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `segment_id` | varchar(64) | NO | — | PRIMARY | — |
| `case_id` | varchar(32) | NO | — | fk_segments_case | 사건 연결 키 |
| `start_turn` | int | NO | — |  | — |
| `end_turn` | int | NO | — |  | — |
| `segment_text` | text | NO | — |  | 분석 구간의 원문 제거 라벨 |
| `risk_score` | decimal(9,6) | NO | — |  | — |
| `model_label` | enum('NORMAL','PHISHING') | NO | — |  | — |
| `evidence_json` | json | NO | — |  | — |
| `created_at` | datetime(6) | NO | — |  | 생성 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `fk_segments_case` | 아니오 | case_id |
| `PRIMARY` | 예 | segment_id |

| FK / CHECK | 정의 |
|---|---|
| `fk_segments_case` | case_id → cases.case_id; DELETE NO ACTION; UPDATE NO ACTION |

<a id="table-context_features"></a>

### context_features

사건·분석 — 정규화된 수치 피처

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 2584행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `feature_id` | bigint | NO | — | PRIMARY / auto_increment | — |
| `case_id` | varchar(32) | NO | — | idx_context_features_case_key | 사건 연결 키 |
| `segment_id` | varchar(64) | YES | — | fk_features_segment | — |
| `feature_key` | varchar(100) | NO | — | idx_context_features_case_key | — |
| `feature_value` | decimal(18,6) | NO | — |  | — |
| `source` | varchar(50) | NO | — |  | 데이터 출처 |
| `created_at` | datetime(6) | NO | — |  | 생성 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `fk_features_segment` | 아니오 | segment_id |
| `idx_context_features_case_key` | 아니오 | case_id, feature_key |
| `PRIMARY` | 예 | feature_id |

| FK / CHECK | 정의 |
|---|---|
| `fk_features_case` | case_id → cases.case_id; DELETE NO ACTION; UPDATE NO ACTION |
| `fk_features_segment` | segment_id → analysis_segments.segment_id; DELETE NO ACTION; UPDATE NO ACTION |

<a id="table-case_semantic_atoms"></a>

### case_semantic_atoms

사건·분석 — 역할·행동·금액·시간을 보존하는 의미 단위

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 129행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `case_id` | varchar(32) | NO | — | idx_case_atoms_turn, PRIMARY, uq_case_atom_fingerprint | 사건 연결 키 |
| `atom_id` | varchar(80) | NO | — | PRIMARY | Case 내부 의미 단위 식별자; 실제 거래 식별자와 동일하지 않음 |
| `atom_class` | varchar(80) | NO | — |  | — |
| `predicate` | varchar(120) | NO | — |  | — |
| `source_turn_id` | int | NO | — | idx_case_atoms_turn | — |
| `semantic_fingerprint` | varchar(128) | NO | — | uq_case_atom_fingerprint | — |
| `payload_json` | json | NO | — |  | 해당 자원의 구조화 payload |
| `source_revision` | bigint | NO | 1 |  | — |
| `created_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) |  / DEFAULT_GENERATED | 생성 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `idx_case_atoms_turn` | 아니오 | case_id, source_turn_id |
| `PRIMARY` | 예 | case_id, atom_id |
| `uq_case_atom_fingerprint` | 예 | case_id, semantic_fingerprint |

| FK / CHECK | 정의 |
|---|---|
| `fk_case_atoms_case` | case_id → cases.case_id; DELETE CASCADE; UPDATE NO ACTION |

<a id="table-case_semantic_relations"></a>

### case_semantic_relations

사건·분석 — 의미 단위 간 순서·인과 등의 관계

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 16행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `case_id` | varchar(32) | NO | — | idx_case_relations_atoms, PRIMARY | 사건 연결 키 |
| `relation_id` | varchar(100) | NO | — | PRIMARY | — |
| `relation_type` | varchar(32) | NO | — |  | — |
| `source_atom_id` | varchar(80) | NO | — | idx_case_relations_atoms | — |
| `target_atom_id` | varchar(80) | NO | — | idx_case_relations_atoms | — |
| `confidence` | decimal(5,4) | NO | — |  | — |
| `payload_json` | json | NO | — |  | 해당 자원의 구조화 payload |
| `source_revision` | bigint | NO | 1 |  | — |
| `created_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) |  / DEFAULT_GENERATED | 생성 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `idx_case_relations_atoms` | 아니오 | case_id, source_atom_id, target_atom_id |
| `PRIMARY` | 예 | case_id, relation_id |

| FK / CHECK | 정의 |
|---|---|
| `fk_case_relations_case` | case_id → cases.case_id; DELETE CASCADE; UPDATE NO ACTION |
| `chk_case_relation_confidence` | `((confidence>=0)and(confidence<=1))` (YES) |

<a id="table-case_context_signals"></a>

### case_context_signals

사건·분석 — 구조화 신호 투영

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 0행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `case_id` | varchar(32) | NO | — | idx_case_signals_state, PRIMARY | 사건 연결 키 |
| `signal_id` | varchar(100) | NO | — | PRIMARY | — |
| `signal_code` | varchar(120) | NO | — |  | — |
| `severity` | varchar(16) | NO | — | idx_case_signals_state | — |
| `confidence` | decimal(5,4) | NO | — |  | — |
| `claim_status` | varchar(32) | NO | — |  | — |
| `visibility` | varchar(32) | NO | BANK_INTERNAL | idx_case_signals_state | 공개 범위 |
| `payload_json` | json | NO | — |  | 해당 자원의 구조화 payload |
| `source_revision` | bigint | NO | 1 |  | — |
| `created_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) |  / DEFAULT_GENERATED | 생성 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `idx_case_signals_state` | 아니오 | case_id, severity, visibility |
| `PRIMARY` | 예 | case_id, signal_id |

| FK / CHECK | 정의 |
|---|---|
| `fk_case_signals_case` | case_id → cases.case_id; DELETE CASCADE; UPDATE NO ACTION |
| `chk_case_signal_confidence` | `((confidence>=0)and(confidence<=1))` (YES) |
| `chk_case_signal_visibility` | `(visibilityin(_utf8mb4\'BANK_INTERNAL\',_utf8mb4\'CUSTOMER_SHARED\',_utf8mb4\'SHARED\'))` (YES) |

<a id="table-bank_staff_directory"></a>

### bank_staff_directory

직원·참여자 — 등록 은행 직원과 배정 가능 직무

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 12행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `staff_id` | varchar(64) | NO | — | PRIMARY | — |
| `display_name` | varchar(100) | NO | — | idx_bank_staff_active | — |
| `assignment_role` | varchar(32) | NO | CONSULTATION |  | 업무 배정 역할; 시스템 권한 role과 별개 |
| `role_label` | varchar(100) | NO | — |  | — |
| `position_title` | varchar(100) | YES | — |  | — |
| `status_text` | varchar(80) | NO | 근무 중 |  | — |
| `status_color_key` | varchar(16) | NO | GREEN |  | — |
| `assignment_eligible` | tinyint(1) | NO | 1 |  | — |
| `linked_user_id` | varchar(64) | YES | — |  | — |
| `created_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) |  / DEFAULT_GENERATED | 생성 시각 |
| `updated_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) |  / DEFAULT_GENERATED | 최종 갱신 시각 |
| `deleted_at` | datetime(6) | YES | — | idx_bank_staff_active | 논리 삭제 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `idx_bank_staff_active` | 아니오 | deleted_at, display_name |
| `PRIMARY` | 예 | staff_id |

| FK / CHECK | 정의 |
|---|---|
| `chk_bank_staff_color` | `(status_color_keyin(_utf8mb4\'GREEN\',_utf8mb4\'BLUE\',_utf8mb4\'YELLOW\',_utf8mb4\'ORANGE\',_utf8mb4\'RED\',_utf8mb4\'PURPLE\',_utf8mb4\'GRAY\'))` (YES) |
| `chk_bank_staff_assignment_role` | `(assignment_rolein(_utf8mb4\'SUPERVISOR\',_utf8mb4\'MONITORING\',_utf8mb4\'CONSULTATION\',_utf8mb4\'OTHER_VIEWER\',_utf8mb4\'HANDOVER_PENDING\'))` (YES) |

<a id="table-case_members"></a>

### case_members

직원·참여자 — Case별 참여자·시스템 권한·배정 역할·제거 상태

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 26행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `case_id` | varchar(32) | NO | — | PRIMARY | 사건 연결 키 |
| `user_id` | varchar(64) | NO | — | PRIMARY | — |
| `display_name` | varchar(80) | NO | — |  | — |
| `role` | varchar(32) | NO | — |  | 참여자의 시스템 권한 역할 |
| `assignment_role` | varchar(32) | NO | HANDOVER_PENDING |  | 업무 배정 역할; 시스템 권한 role과 별개 |
| `status` | varchar(32) | NO | ACTIVE |  | 자원별 처리 상태 |
| `assigned_at` | datetime(6) | NO | — |  | — |
| `updated_at` | datetime(6) | NO | — |  | 최종 갱신 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `PRIMARY` | 예 | case_id, user_id |

| FK / CHECK | 정의 |
|---|---|
| `fk_case_members_case` | case_id → cases.case_id; DELETE NO ACTION; UPDATE NO ACTION |
| `chk_case_member_assignment_role` | `(assignment_rolein(_utf8mb4\'SUPERVISOR\',_utf8mb4\'MONITORING\',_utf8mb4\'CONSULTATION\',_utf8mb4\'VIEWER\',_utf8mb4\'HANDOVER_PENDING\'))` (YES) |

<a id="table-case_presence"></a>

### case_presence

직원·참여자 — 사용자 접속·만료 시각; 담당자 배정과 별개

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 22행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `case_id` | varchar(32) | NO | — | idx_case_presence_expiry, PRIMARY | 사건 연결 키 |
| `user_id` | varchar(64) | NO | — | PRIMARY | — |
| `display_name` | varchar(80) | NO | — |  | — |
| `presence` | varchar(16) | NO | — |  | — |
| `channel` | varchar(32) | NO | — |  | — |
| `last_seen_at` | datetime(6) | NO | — |  | — |
| `expires_at` | datetime(6) | NO | — | idx_case_presence_expiry | — |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `idx_case_presence_expiry` | 아니오 | case_id, expires_at |
| `PRIMARY` | 예 | case_id, user_id |

| FK / CHECK | 정의 |
|---|---|
| `fk_case_presence_case` | case_id → cases.case_id; DELETE NO ACTION; UPDATE NO ACTION |

<a id="table-messages"></a>

### messages

대화·고객 질문 — 고객/은행/AI 대화와 시스템 이벤트; 통화 입력 원문과 별개; attachments_json은 현재 빈 호환 필드

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 202행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `message_id` | varchar(64) | NO | — | idx_messages_case_cursor, PRIMARY | — |
| `case_id` | varchar(32) | NO | — | idx_messages_case_cursor, uq_messages_case_client_request | 사건 연결 키 |
| `actor_type` | varchar(32) | NO | — |  | — |
| `content` | text | NO | — |  | — |
| `channel` | varchar(32) | NO | CUSTOMER |  | — |
| `audience` | varchar(32) | NO | CUSTOMER |  | — |
| `mentions_json` | text | YES | — |  | — |
| `reply_to_message_id` | varchar(64) | YES | — |  | — |
| `client_request_id` | varchar(100) | YES | — | uq_messages_case_client_request | 재요청 중복 방지 키 |
| `created_at` | datetime(6) | NO | — | idx_messages_case_cursor | 생성 시각 |
| `actor_user_id` | varchar(64) | YES | — |  | — |
| `actor_display_name` | varchar(80) | YES | — |  | — |
| `actor_role` | varchar(64) | YES | — |  | — |
| `visibility` | varchar(32) | NO | CUSTOMER |  | 공개 범위 |
| `message_kind` | varchar(32) | NO | CHAT |  | — |
| `private_owner_user_id` | varchar(64) | YES | — |  | — |
| `attachments_json` | json | YES | — |  | 구버전 채팅 계약 호환 필드; 현재는 빈 값만 유지하고 첨부 데이터 저장 금지 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `idx_messages_case_cursor` | 아니오 | case_id, created_at, message_id |
| `PRIMARY` | 예 | message_id |
| `uq_messages_case_client_request` | 예 | case_id, client_request_id |

| FK / CHECK | 정의 |
|---|---|
| `fk_messages_case` | case_id → cases.case_id; DELETE NO ACTION; UPDATE NO ACTION |

<a id="table-customer_questions"></a>

### customer_questions

대화·고객 질문 — 고객 질문·선택지·답변·질문 버전

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 20행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `question_id` | varchar(100) | NO | — | PRIMARY | — |
| `case_id` | varchar(32) | NO | — | idx_customer_questions_case | 사건 연결 키 |
| `source` | varchar(32) | NO | — |  | 데이터 출처 |
| `target_field` | varchar(100) | NO | — |  | — |
| `question_text` | text | NO | — |  | — |
| `reason` | text | NO | — |  | — |
| `priority` | varchar(2) | NO | — |  | — |
| `status` | varchar(16) | NO | PENDING |  | 자원별 처리 상태 |
| `sequence` | int | NO | — | idx_customer_questions_case | — |
| `requested_by` | varchar(80) | YES | — |  | — |
| `asked_at` | datetime(6) | YES | — |  | — |
| `answered_at` | datetime(6) | YES | — |  | — |
| `options_json` | json | NO | — |  | — |
| `allow_multi_select` | tinyint(1) | NO | 0 |  | — |
| `question_message_id` | varchar(64) | YES | — |  | — |
| `answer_message_id` | varchar(64) | YES | — |  | — |
| `answer_text` | text | YES | — |  | — |
| `question_version` | bigint | NO | 1 |  | — |
| `answer_payload_json` | json | YES | — |  | — |
| `answer_question_version` | bigint | YES | — |  | — |
| `created_at` | datetime(6) | NO | — |  | 생성 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `idx_customer_questions_case` | 아니오 | case_id, sequence |
| `PRIMARY` | 예 | question_id |

| FK / CHECK | 정의 |
|---|---|
| `fk_customer_questions_case` | case_id → cases.case_id; DELETE NO ACTION; UPDATE NO ACTION |

<a id="table-message_context_extractions"></a>

### message_context_extractions

대화·고객 질문 — 메시지→사실 후보 추출 작업·재시도 상태

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 142행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `extraction_id` | varchar(64) | NO | — | PRIMARY | — |
| `case_id` | varchar(32) | NO | — | idx_message_context_extraction_case | 사건 연결 키 |
| `message_id` | varchar(64) | NO | — | uq_message_context_extraction_message | — |
| `status` | varchar(16) | NO | PENDING | idx_message_context_extraction_retry | 자원별 처리 상태 |
| `attempts` | int | NO | 0 | idx_message_context_extraction_retry | — |
| `last_error` | varchar(1000) | YES | — |  | 마지막 처리 오류; 민감 원문을 넣지 않음 |
| `model_version` | varchar(100) | YES | — |  | — |
| `prompt_version` | varchar(100) | YES | — |  | — |
| `created_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) | idx_message_context_extraction_case / DEFAULT_GENERATED | 생성 시각 |
| `updated_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) | idx_message_context_extraction_retry / DEFAULT_GENERATED | 최종 갱신 시각 |
| `completed_at` | datetime(6) | YES | — |  | — |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `idx_message_context_extraction_case` | 아니오 | case_id, created_at |
| `idx_message_context_extraction_retry` | 아니오 | status, attempts, updated_at |
| `PRIMARY` | 예 | extraction_id |
| `uq_message_context_extraction_message` | 예 | message_id |

| FK / CHECK | 정의 |
|---|---|
| `fk_message_context_extraction_case` | case_id → cases.case_id; DELETE CASCADE; UPDATE NO ACTION |
| `fk_message_context_extraction_message` | message_id → messages.message_id; DELETE CASCADE; UPDATE NO ACTION |
| `chk_message_context_extraction_status` | `(statusin(_utf8mb4\'PENDING\',_utf8mb4\'PROCESSING\',_utf8mb4\'COMPLETED\',_utf8mb4\'FAILED\',_utf8mb4\'SKIPPED\'))` (YES) |
| `chk_message_context_extraction_attempts` | `(attemptsbetween0and3)` (YES) |

<a id="table-case_transactions"></a>

### case_transactions

금액·거래 — 외부 은행 원장이 아닌 Case 내부 확인 거래 기록; Context V2 실제 금액 사실을 직원 확인 후 승격

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 0행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `id` | bigint unsigned | NO | — | PRIMARY / auto_increment | — |
| `case_id` | varchar(32) | NO | — | idx_case_transactions_case_at | 사건 연결 키 |
| `transaction_type` | varchar(32) | NO | — |  | 송금/반환 등 거래 유형; TRANSFER_OUT·RETURN_IN·CANCELLED만 허용 |
| `transaction_at` | datetime(6) | NO | — | idx_case_transactions_case_at | 거래 시각; 원문 발화 시각과 구분 |
| `amount` | bigint | NO | — |  | 개별 거래 금액; KRW 정수(BIGINT), 합계 정책은 별도 |
| `account_number` | varchar(100) | YES | — |  | — |
| `counterparty_name` | varchar(100) | YES | — |  | — |
| `counterparty_account` | varchar(100) | YES | — |  | — |
| `bank_name` | varchar(100) | YES | — |  | — |
| `memo` | varchar(500) | YES | — |  | — |
| `source` | varchar(32) | NO | MANUAL |  | 데이터 출처 |
| `created_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) |  / DEFAULT_GENERATED | 생성 시각 |
| `updated_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) |  / DEFAULT_GENERATED | 최종 갱신 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `idx_case_transactions_case_at` | 아니오 | case_id, transaction_at |
| `PRIMARY` | 예 | id |

| FK / CHECK | 정의 |
|---|---|
| `fk_case_transactions_case` | case_id → cases.case_id; DELETE CASCADE; UPDATE NO ACTION |
| `chk_case_transactions_type` | `(transaction_typein(_utf8mb4\'TRANSFER_OUT\',_utf8mb4\'RETURN_IN\',_utf8mb4\'CANCELLED\'))` (YES) |
| `chk_case_transactions_amount` | `(amount>=0)` (YES) |

<a id="table-case_context_facts_v2"></a>

### case_context_facts_v2

사실·확인 — AI·대화·직원 확인에서 나온 사실 후보·확정·기각·대체 상태와 근거; 거래 승격 전의 기준 원장

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 264행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `fact_id` | varchar(64) | NO | — | PRIMARY | — |
| `case_id` | varchar(32) | NO | — | idx_context_facts_case_state, uq_context_fact_request | 사건 연결 키 |
| `semantic_key` | varchar(160) | NO | — | idx_context_facts_case_state | 사실/화면 항목 분류 키 |
| `display_label` | varchar(255) | NO | — |  | — |
| `value_json` | json | NO | — |  | 타입별 구조화 값; 금액 후보는 amount_krw와 상태·근거를 함께 해석 |
| `display_value` | text | NO | — |  | — |
| `source_kind` | varchar(32) | NO | — |  | 추출·진술·직원 관찰·공식 기록 등의 출처 |
| `status` | varchar(16) | NO | PROPOSED | idx_context_facts_case_state | 자원별 처리 상태 |
| `confidence` | decimal(5,4) | YES | — |  | — |
| `evidence_refs_json` | json | NO | — |  | 근거 종류·ID 목록; 일부는 논리 참조이며 DB FK가 아님 |
| `visibility` | varchar(32) | NO | BANK_INTERNAL |  | 공개 범위 |
| `confirmed_by` | varchar(64) | YES | — |  | 확인 담당자 |
| `confirmed_at` | datetime(6) | YES | — |  | 확인 시각 |
| `rejection_reason` | varchar(1000) | YES | — |  | — |
| `supersedes_fact_id` | varchar(64) | YES | — | fk_context_fact_v2_supersedes | 대체 관계; 삭제 대신 이력 유지 |
| `client_request_id` | varchar(100) | YES | — | uq_context_fact_request | 재요청 중복 방지 키 |
| `version` | bigint | NO | 1 |  | 낙관적 잠금/수정 버전 |
| `created_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) |  / DEFAULT_GENERATED | 생성 시각 |
| `updated_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) |  / DEFAULT_GENERATED | 최종 갱신 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `fk_context_fact_v2_supersedes` | 아니오 | supersedes_fact_id |
| `idx_context_facts_case_state` | 아니오 | case_id, status, semantic_key |
| `PRIMARY` | 예 | fact_id |
| `uq_context_fact_request` | 예 | case_id, client_request_id |

| FK / CHECK | 정의 |
|---|---|
| `fk_context_fact_v2_case` | case_id → cases.case_id; DELETE CASCADE; UPDATE NO ACTION |
| `fk_context_fact_v2_supersedes` | supersedes_fact_id → case_context_facts_v2.fact_id; DELETE SET NULL; UPDATE NO ACTION |
| `chk_context_fact_status` | `(statusin(_utf8mb4\'PROPOSED\',_utf8mb4\'CONFIRMED\',_utf8mb4\'REJECTED\',_utf8mb4\'SUPERSEDED\'))` (YES) |
| `chk_context_fact_source` | `(source_kindin(_utf8mb4\'AI_EXTRACTION\',_utf8mb4\'CUSTOMER_STATEMENT\',_utf8mb4\'STAFF_OBSERVATION\',_utf8mb4\'BANK_RECORD\',_utf8mb4\'OFFICIAL_VERIFICATION\'))` (YES) |
| `chk_context_fact_visibility` | `(visibilityin(_utf8mb4\'BANK_INTERNAL\',_utf8mb4\'CUSTOMER_SHARED\'))` (YES) |
| `chk_context_fact_confidence` | `((confidenceisnull)or((confidence>=0)and(confidence<=1)))` (YES) |
| `chk_context_fact_confirmed` | `((status<>_utf8mb4\'CONFIRMED\')or((confirmed_byisnotnull)and(confirmed_atisnotnull)))` (YES) |
| `chk_context_fact_rejected` | `((status<>_utf8mb4\'REJECTED\')or(rejection_reasonisnotnull))` (YES) |

<a id="table-case_gaps"></a>

### case_gaps

사실·확인 — 미확인 사항과 해소 근거

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 0행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `gap_id` | varchar(64) | NO | — | PRIMARY | — |
| `case_id` | varchar(32) | NO | — | idx_case_gaps_state, uq_case_gap_active, uq_case_gap_request | 사건 연결 키 |
| `semantic_key` | varchar(160) | NO | — |  | 사실/화면 항목 분류 키 |
| `title` | varchar(300) | NO | — |  | — |
| `reason` | text | NO | — |  | — |
| `priority` | varchar(16) | NO | — | idx_case_gaps_state | — |
| `status` | varchar(32) | NO | OPEN | idx_case_gaps_state | 자원별 처리 상태 |
| `source` | varchar(24) | NO | — |  | 데이터 출처 |
| `evidence_refs_json` | json | NO | — |  | 근거 종류·ID 목록; 일부는 논리 참조이며 DB FK가 아님 |
| `related_question_ids_json` | json | NO | — |  | — |
| `related_verification_ids_json` | json | NO | — |  | — |
| `resolution_fact_id` | varchar(64) | YES | — | fk_case_gap_resolution | — |
| `dismissal_reason` | varchar(1000) | YES | — |  | — |
| `visibility` | varchar(32) | NO | BANK_INTERNAL |  | 공개 범위 |
| `source_revision` | bigint | NO | — |  | — |
| `client_request_id` | varchar(100) | YES | — | uq_case_gap_request | 재요청 중복 방지 키 |
| `version` | bigint | NO | 1 |  | 낙관적 잠금/수정 버전 |
| `created_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) |  / DEFAULT_GENERATED | 생성 시각 |
| `updated_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) |  / DEFAULT_GENERATED | 최종 갱신 시각 |
| `active_semantic_key` | varchar(160) | YES | — | uq_case_gap_active / STORED GENERATED | — |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `fk_case_gap_resolution` | 아니오 | resolution_fact_id |
| `idx_case_gaps_state` | 아니오 | case_id, status, priority |
| `PRIMARY` | 예 | gap_id |
| `uq_case_gap_active` | 예 | case_id, active_semantic_key |
| `uq_case_gap_request` | 예 | case_id, client_request_id |

| FK / CHECK | 정의 |
|---|---|
| `fk_case_gap_case` | case_id → cases.case_id; DELETE CASCADE; UPDATE NO ACTION |
| `fk_case_gap_resolution` | resolution_fact_id → case_context_facts_v2.fact_id; DELETE RESTRICT; UPDATE NO ACTION |
| `chk_case_gap_status` | `(statusin(_utf8mb4\'OPEN\',_utf8mb4\'AWAITING_CUSTOMER\',_utf8mb4\'AWAITING_INSTITUTION\',_utf8mb4\'STAFF_REVIEW_REQUIRED\',_utf8mb4\'RESOLVED\',_utf8mb4\'DISMISSED\'))` (YES) |
| `chk_case_gap_priority` | `(priorityin(_utf8mb4\'URGENT\',_utf8mb4\'HIGH\',_utf8mb4\'NORMAL\'))` (YES) |
| `chk_case_gap_source` | `(sourcein(_utf8mb4\'AI\',_utf8mb4\'BANK_STAFF\',_utf8mb4\'SYSTEM_RULE\'))` (YES) |
| `chk_case_gap_visibility` | `(visibility=_utf8mb4\'BANK_INTERNAL\')` (YES) |
| `chk_case_gap_resolved` | `((status<>_utf8mb4\'RESOLVED\')or(resolution_fact_idisnotnull))` (YES) |
| `chk_case_gap_dismissed` | `((status<>_utf8mb4\'DISMISSED\')or(dismissal_reasonisnotnull))` (YES) |

<a id="table-verification_tasks"></a>

### verification_tasks

사실·확인 — 별도 확인 업무·결과·공개 여부

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 0행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `verification_task_id` | varchar(64) | NO | — | PRIMARY | — |
| `case_id` | varchar(32) | NO | — | idx_verification_tasks_case | 사건 연결 키 |
| `claim` | text | NO | — |  | — |
| `target` | varchar(255) | NO | — |  | — |
| `status` | varchar(32) | NO | PENDING |  | 자원별 처리 상태 |
| `version` | int | NO | 1 |  | 낙관적 잠금/수정 버전 |
| `created_at` | datetime(6) | NO | — | idx_verification_tasks_case | 생성 시각 |
| `updated_at` | datetime(6) | NO | — |  | 최종 갱신 시각 |
| `result_summary` | text | YES | — |  | — |
| `evidence_url` | varchar(2000) | YES | — |  | — |
| `verified_by` | varchar(80) | YES | — |  | — |
| `rag_source` | varchar(255) | YES | — |  | — |
| `customer_visible` | tinyint(1) | NO | 0 |  | — |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `idx_verification_tasks_case` | 아니오 | case_id, created_at |
| `PRIMARY` | 예 | verification_task_id |

| FK / CHECK | 정의 |
|---|---|
| `fk_verification_tasks_case` | case_id → cases.case_id; DELETE NO ACTION; UPDATE NO ACTION |

<a id="table-case_context_observations"></a>

### case_context_observations

사실·확인 — 표준 분류에 매핑되지 않은 구조화 관찰

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 0행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `observation_id` | varchar(100) | NO | — | PRIMARY | — |
| `case_id` | varchar(32) | NO | — | idx_context_observations_review, PRIMARY | 사건 연결 키 |
| `observation_type` | varchar(80) | NO | — |  | — |
| `payload_json` | json | NO | — |  | 해당 자원의 구조화 payload |
| `status` | varchar(16) | NO | UNMAPPED | idx_context_observations_review | 자원별 처리 상태 |
| `created_by` | varchar(64) | NO | — |  | — |
| `created_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) | idx_context_observations_review / DEFAULT_GENERATED | 생성 시각 |
| `updated_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) |  / DEFAULT_GENERATED | 최종 갱신 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `idx_context_observations_review` | 아니오 | case_id, status, created_at |
| `PRIMARY` | 예 | case_id, observation_id |

| FK / CHECK | 정의 |
|---|---|
| `fk_context_observations_case` | case_id → cases.case_id; DELETE CASCADE; UPDATE NO ACTION |
| `chk_context_observations_status` | `(statusin(_utf8mb4\'UNMAPPED\',_utf8mb4\'REVIEWED\',_utf8mb4\'MAPPED\',_utf8mb4\'DISMISSED\'))` (YES) |

<a id="table-actions"></a>

### actions

조치·업무·결정 — 기존 조치 저널·고객 진행 상태 등; 실제 외부 실행 증거와 구분

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 157행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `action_id` | varchar(64) | NO | — | idx_actions_case_cursor, PRIMARY | — |
| `case_id` | varchar(32) | NO | — | idx_actions_case_cursor | 사건 연결 키 |
| `action_type` | varchar(64) | NO | — |  | — |
| `title` | varchar(300) | YES | — |  | — |
| `status` | varchar(32) | NO | REQUESTED |  | 자원별 처리 상태 |
| `actor_type` | varchar(32) | NO | — |  | — |
| `version` | bigint | NO | 1 |  | 낙관적 잠금/수정 버전 |
| `note` | text | NO | — |  | — |
| `created_at` | datetime(6) | NO | — | idx_actions_case_cursor | 생성 시각 |
| `updated_at` | datetime(6) | NO | — |  | 최종 갱신 시각 |
| `updated_by` | varchar(128) | YES | — |  | — |
| `visibility` | varchar(32) | NO | BANK_INTERNAL |  | 공개 범위 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `idx_actions_case_cursor` | 아니오 | case_id, created_at, action_id |
| `PRIMARY` | 예 | action_id |

| FK / CHECK | 정의 |
|---|---|
| `fk_actions_case` | case_id → cases.case_id; DELETE NO ACTION; UPDATE NO ACTION |
| `chk_actions_version` | `(version>=1)` (YES) |
| `chk_actions_visibility` | `(visibilityin(_utf8mb4\'BANK_INTERNAL\',_utf8mb4\'CUSTOMER_SHARED\'))` (YES) |

<a id="table-case_ai_suggestions"></a>

### case_ai_suggestions

조치·업무·결정 — AI 업무 제안·검토·채택 상태

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 0행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `suggestion_id` | varchar(64) | NO | — | PRIMARY | — |
| `case_id` | varchar(32) | NO | — | idx_ai_suggestions_state, uq_ai_suggestion_active | 사건 연결 키 |
| `suggestion_type` | varchar(40) | NO | — |  | — |
| `title` | varchar(300) | NO | — |  | — |
| `rationale` | text | NO | — |  | — |
| `priority` | varchar(16) | NO | — | idx_ai_suggestions_state | — |
| `status` | varchar(16) | NO | PROPOSED | idx_ai_suggestions_state | 자원별 처리 상태 |
| `related_gap_ids_json` | json | NO | — |  | — |
| `evidence_refs_json` | json | NO | — |  | 근거 종류·ID 목록; 일부는 논리 참조이며 DB FK가 아님 |
| `dedupe_key` | varchar(255) | NO | — |  | — |
| `execution_mode` | varchar(40) | NO | HUMAN_REVIEW_REQUIRED |  | — |
| `source_revision` | bigint | NO | — |  | — |
| `model_version` | varchar(100) | YES | — |  | — |
| `prompt_version` | varchar(100) | YES | — |  | — |
| `accepted_task_id` | varchar(64) | YES | — |  | — |
| `reviewed_by` | varchar(64) | YES | — |  | — |
| `reviewed_at` | datetime(6) | YES | — |  | — |
| `dismissal_reason` | varchar(1000) | YES | — |  | — |
| `version` | bigint | NO | 1 |  | 낙관적 잠금/수정 버전 |
| `created_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) |  / DEFAULT_GENERATED | 생성 시각 |
| `updated_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) |  / DEFAULT_GENERATED | 최종 갱신 시각 |
| `active_dedupe_key` | varchar(255) | YES | — | uq_ai_suggestion_active / STORED GENERATED | — |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `idx_ai_suggestions_state` | 아니오 | case_id, status, priority |
| `PRIMARY` | 예 | suggestion_id |
| `uq_ai_suggestion_active` | 예 | case_id, active_dedupe_key |

| FK / CHECK | 정의 |
|---|---|
| `fk_ai_suggestion_case` | case_id → cases.case_id; DELETE CASCADE; UPDATE NO ACTION |
| `chk_ai_suggestion_type` | `(suggestion_typein(_utf8mb4\'CUSTOMER_QUESTION\',_utf8mb4\'INSTITUTION_VERIFICATION\',_utf8mb4\'TRANSACTION_REVIEW\',_utf8mb4\'PROTECTIVE_ACTION\',_utf8mb4\'DOCUMENT_REQUEST\',_utf8mb4\'STAFF_REVIEW\'))` (YES) |
| `chk_ai_suggestion_priority` | `(priorityin(_utf8mb4\'URGENT\',_utf8mb4\'HIGH\',_utf8mb4\'NORMAL\'))` (YES) |
| `chk_ai_suggestion_status` | `(statusin(_utf8mb4\'PROPOSED\',_utf8mb4\'ACCEPTED\',_utf8mb4\'DISMISSED\',_utf8mb4\'EXPIRED\',_utf8mb4\'SUPERSEDED\'))` (YES) |
| `chk_ai_suggestion_mode` | `(execution_modein(_utf8mb4\'HUMAN_REVIEW_REQUIRED\',_utf8mb4\'AUTO_CUSTOMER_QUESTION_ALLOWED\'))` (YES) |
| `chk_ai_suggestion_review` | `((statusnotin(_utf8mb4\'ACCEPTED\',_utf8mb4\'DISMISSED\'))or((reviewed_byisnotnull)and(reviewed_atisnotnull)))` (YES) |
| `chk_ai_suggestion_dismissed` | `((status<>_utf8mb4\'DISMISSED\')or(dismissal_reasonisnotnull))` (YES) |

<a id="table-case_tasks"></a>

### case_tasks

조치·업무·결정 — 담당자 업무·진행·완료·차단 상태

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 0행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `task_id` | varchar(64) | NO | — | PRIMARY | — |
| `case_id` | varchar(32) | NO | — | idx_case_tasks_assignee, idx_case_tasks_state, uq_case_task_request | 사건 연결 키 |
| `source` | varchar(32) | NO | — |  | 데이터 출처 |
| `source_suggestion_id` | varchar(64) | YES | — | fk_case_task_suggestion | — |
| `task_type` | varchar(40) | NO | — |  | — |
| `title` | varchar(300) | NO | — |  | — |
| `description` | text | NO | — |  | — |
| `priority` | varchar(16) | NO | — | idx_case_tasks_state | — |
| `status` | varchar(16) | NO | TODO | idx_case_tasks_assignee, idx_case_tasks_state | 자원별 처리 상태 |
| `assignee_user_id` | varchar(64) | YES | — | idx_case_tasks_assignee | — |
| `due_at` | datetime(6) | YES | — |  | — |
| `related_gap_ids_json` | json | NO | — |  | — |
| `related_verification_ids_json` | json | NO | — |  | — |
| `result_code` | varchar(100) | YES | — |  | — |
| `result_summary` | text | YES | — |  | — |
| `evidence_refs_json` | json | NO | — |  | 근거 종류·ID 목록; 일부는 논리 참조이며 DB FK가 아님 |
| `customer_visibility` | varchar(32) | NO | INTERNAL_ONLY |  | — |
| `completed_by` | varchar(64) | YES | — |  | — |
| `completed_at` | datetime(6) | YES | — |  | — |
| `cancellation_reason` | varchar(1000) | YES | — |  | — |
| `client_request_id` | varchar(100) | YES | — | uq_case_task_request | 재요청 중복 방지 키 |
| `version` | bigint | NO | 1 |  | 낙관적 잠금/수정 버전 |
| `created_by` | varchar(64) | NO | — |  | — |
| `created_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) |  / DEFAULT_GENERATED | 생성 시각 |
| `updated_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) | idx_case_tasks_state / DEFAULT_GENERATED | 최종 갱신 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `fk_case_task_suggestion` | 아니오 | source_suggestion_id |
| `idx_case_tasks_assignee` | 아니오 | case_id, assignee_user_id, status |
| `idx_case_tasks_state` | 아니오 | case_id, status, priority, updated_at |
| `PRIMARY` | 예 | task_id |
| `uq_case_task_request` | 예 | case_id, client_request_id |

| FK / CHECK | 정의 |
|---|---|
| `fk_case_task_case` | case_id → cases.case_id; DELETE CASCADE; UPDATE NO ACTION |
| `fk_case_task_suggestion` | source_suggestion_id → case_ai_suggestions.suggestion_id; DELETE SET NULL; UPDATE NO ACTION |
| `chk_case_task_source` | `(sourcein(_utf8mb4\'STAFF_CREATED\',_utf8mb4\'AI_SUGGESTION_ACCEPTED\',_utf8mb4\'SYSTEM_REQUIRED\'))` (YES) |
| `chk_case_task_type` | `(task_typein(_utf8mb4\'CUSTOMER_CONTACT\',_utf8mb4\'INSTITUTION_VERIFICATION\',_utf8mb4\'TRANSACTION_REVIEW\',_utf8mb4\'PROTECTIVE_ACTION\',_utf8mb4\'DOCUMENT_REVIEW\',_utf8mb4\'OTHER\'))` (YES) |
| `chk_case_task_priority` | `(priorityin(_utf8mb4\'URGENT\',_utf8mb4\'HIGH\',_utf8mb4\'NORMAL\'))` (YES) |
| `chk_case_task_status` | `(statusin(_utf8mb4\'TODO\',_utf8mb4\'IN_PROGRESS\',_utf8mb4\'BLOCKED\',_utf8mb4\'COMPLETED\',_utf8mb4\'CANCELLED\'))` (YES) |
| `chk_case_task_visibility` | `(customer_visibilityin(_utf8mb4\'INTERNAL_ONLY\',_utf8mb4\'RESULT_SHAREABLE\',_utf8mb4\'RESULT_PUBLISHED\'))` (YES) |
| `chk_case_task_completed` | `((status<>_utf8mb4\'COMPLETED\')or((result_summaryisnotnull)and(completed_byisnotnull)and(completed_atisnotnull)))` (YES) |
| `chk_case_task_cancelled` | `((status<>_utf8mb4\'CANCELLED\')or(cancellation_reasonisnotnull))` (YES) |

<a id="table-case_decisions"></a>

### case_decisions

조치·업무·결정 — 직원 판단·결정 기록

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 0행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `decision_id` | varchar(64) | NO | — | idx_case_decisions_created, PRIMARY | — |
| `case_id` | varchar(32) | NO | — | idx_case_decisions_created, uq_case_decision_request | 사건 연결 키 |
| `decision_type` | varchar(32) | NO | — |  | — |
| `title` | varchar(300) | NO | — |  | — |
| `rationale` | text | NO | — |  | — |
| `related_entity_type` | varchar(24) | NO | — |  | — |
| `related_entity_id` | varchar(100) | NO | — |  | — |
| `visibility` | varchar(32) | NO | BANK_INTERNAL |  | 공개 범위 |
| `actor_user_id` | varchar(64) | NO | — |  | — |
| `supersedes_decision_id` | varchar(64) | YES | — | fk_case_decision_supersedes | — |
| `client_request_id` | varchar(100) | NO | — | uq_case_decision_request | 재요청 중복 방지 키 |
| `created_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) | idx_case_decisions_created / DEFAULT_GENERATED | 생성 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `fk_case_decision_supersedes` | 아니오 | supersedes_decision_id |
| `idx_case_decisions_created` | 아니오 | case_id, created_at, decision_id |
| `PRIMARY` | 예 | decision_id |
| `uq_case_decision_request` | 예 | case_id, client_request_id |

| FK / CHECK | 정의 |
|---|---|
| `fk_case_decision_case` | case_id → cases.case_id; DELETE CASCADE; UPDATE NO ACTION |
| `fk_case_decision_supersedes` | supersedes_decision_id → case_decisions.decision_id; DELETE SET NULL; UPDATE NO ACTION |
| `chk_case_decision_type` | `(decision_typein(_utf8mb4\'FACT_REVIEW\',_utf8mb4\'TASK_DECISION\',_utf8mb4\'CASE_STATUS\',_utf8mb4\'CUSTOMER_DISCLOSURE\',_utf8mb4\'OTHER\'))` (YES) |
| `chk_case_decision_entity` | `(related_entity_typein(_utf8mb4\'FACT\',_utf8mb4\'GAP\',_utf8mb4\'SUGGESTION\',_utf8mb4\'TASK\',_utf8mb4\'VERIFICATION\',_utf8mb4\'CASE\'))` (YES) |
| `chk_case_decision_visibility` | `(visibilityin(_utf8mb4\'BANK_INTERNAL\',_utf8mb4\'CUSTOMER_SHARED\'))` (YES) |

<a id="table-case_context_items"></a>

### case_context_items

화면·캐시 — 직원 표시 편집본과 버전; 원본 사실과 별개

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 0행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `item_id` | varchar(64) | NO | — | PRIMARY | — |
| `case_id` | varchar(32) | NO | — | uq_context_semantic | 사건 연결 키 |
| `section` | varchar(32) | NO | — | uq_context_semantic | — |
| `semantic_key` | varchar(160) | NO | — | uq_context_semantic | 사실/화면 항목 분류 키 |
| `item_version` | bigint | NO | — |  | — |
| `state_json` | json | NO | — |  | 표시 편집본 상태 |
| `updated_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) |  / DEFAULT_GENERATED | 최종 갱신 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `PRIMARY` | 예 | item_id |
| `uq_context_semantic` | 예 | case_id, section, semantic_key |

| FK / CHECK | 정의 |
|---|---|
| `fk_context_item_case` | case_id → cases.case_id; DELETE NO ACTION; UPDATE NO ACTION |

<a id="table-case_context_projections"></a>

### case_context_projections

화면·캐시 — 맥락 생성 lease·revision·마지막 성공 결과 캐시; 원본 사실·직원 이력과 별개

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 17행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `case_id` | varchar(32) | NO | — | PRIMARY | 사건 연결 키 |
| `generation_status` | varchar(16) | NO | EMPTY |  | — |
| `generating_revision` | bigint | YES | — |  | — |
| `lease_token` | varchar(64) | YES | — |  | — |
| `lease_expires_at` | datetime(6) | YES | — |  | — |
| `last_success_revision` | bigint | YES | — |  | — |
| `last_success_payload` | json | YES | — |  | — |
| `schema_version` | varchar(32) | NO | case-support.v1 |  | — |
| `model_version` | varchar(100) | YES | — |  | — |
| `prompt_version` | varchar(100) | YES | — |  | — |
| `last_error` | varchar(500) | YES | — |  | 마지막 처리 오류; 민감 원문을 넣지 않음 |
| `generated_at` | datetime(6) | YES | — |  | — |
| `updated_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) |  / DEFAULT_GENERATED | 최종 갱신 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `PRIMARY` | 예 | case_id |

| FK / CHECK | 정의 |
|---|---|
| `fk_context_projection_case` | case_id → cases.case_id; DELETE NO ACTION; UPDATE NO ACTION |

<a id="table-personal_notes"></a>

### personal_notes

화면·캐시 — 작성자 개인 메모

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 0행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `note_id` | varchar(100) | NO | — | PRIMARY | — |
| `case_id` | varchar(32) | NO | — | idx_personal_notes_author | 사건 연결 키 |
| `author_id` | varchar(80) | NO | — | idx_personal_notes_author | — |
| `content` | text | NO | — |  | — |
| `visibility` | varchar(32) | NO | PRIVATE_TO_AUTHOR |  | 공개 범위 |
| `created_at` | datetime(6) | NO | — |  | 생성 시각 |
| `updated_at` | datetime(6) | NO | — | idx_personal_notes_author | 최종 갱신 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `idx_personal_notes_author` | 아니오 | case_id, author_id, updated_at |
| `PRIMARY` | 예 | note_id |

| FK / CHECK | 정의 |
|---|---|
| `fk_personal_notes_case` | case_id → cases.case_id; DELETE NO ACTION; UPDATE NO ACTION |

<a id="table-case_reports"></a>

### case_reports

보고서·이력 — LIVE/FINAL 보고서 원장; live_report는 초기 분석 snapshot이며 우측 Context Panel의 공개 계약과 분리

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 17행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `report_id` | varchar(64) | NO | — | PRIMARY | — |
| `case_id` | varchar(32) | NO | — | uq_case_live_report | 사건 연결 키 |
| `report_type` | enum('LIVE','FINAL') | NO | LIVE | uq_case_live_report | — |
| `report_version` | int | NO | 1 |  | — |
| `created_at` | datetime(6) | NO | — |  | 생성 시각 |
| `updated_at` | datetime(6) | NO | — |  | 최종 갱신 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `PRIMARY` | 예 | report_id |
| `uq_case_live_report` | 예 | case_id, report_type |

| FK / CHECK | 정의 |
|---|---|
| `fk_case_reports_case` | case_id → cases.case_id; DELETE NO ACTION; UPDATE NO ACTION |

<a id="table-case_report_sections"></a>

### case_report_sections

보고서·이력 — 보고서 섹션 JSON·버전

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 119행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `report_id` | varchar(64) | NO | — | PRIMARY | — |
| `section_key` | varchar(64) | NO | — | PRIMARY | — |
| `content_json` | json | NO | — |  | — |
| `section_version` | int | NO | 1 |  | — |
| `updated_at` | datetime(6) | NO | — |  | 최종 갱신 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `PRIMARY` | 예 | report_id, section_key |

| FK / CHECK | 정의 |
|---|---|
| `fk_report_sections_report` | report_id → case_reports.report_id; DELETE NO ACTION; UPDATE NO ACTION |

<a id="table-case_events"></a>

### case_events

보고서·이력 — Case 업무 이벤트 타임라인

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 435행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `event_id` | bigint | NO | — | idx_case_events_case_cursor, PRIMARY / auto_increment | — |
| `case_id` | varchar(32) | NO | — | idx_case_events_case_cursor | 사건 연결 키 |
| `event_type` | varchar(64) | NO | — |  | — |
| `actor_type` | varchar(32) | NO | SYSTEM |  | — |
| `payload_json` | json | NO | — |  | 해당 자원의 구조화 payload |
| `occurred_at` | datetime(6) | NO | — |  | — |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `idx_case_events_case_cursor` | 아니오 | case_id, event_id |
| `PRIMARY` | 예 | event_id |

| FK / CHECK | 정의 |
|---|---|
| `fk_case_events_case` | case_id → cases.case_id; DELETE NO ACTION; UPDATE NO ACTION |

<a id="table-case_context_item_history"></a>

### case_context_item_history

보고서·이력 — 직원 표시 편집 변경 이력

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 0행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `history_id` | bigint | NO | — | PRIMARY / auto_increment | — |
| `item_id` | varchar(64) | NO | — | uq_context_history_version | — |
| `item_version` | bigint | NO | — | uq_context_history_version | — |
| `operation` | varchar(24) | NO | — |  | — |
| `actor_id` | varchar(64) | NO | — |  | — |
| `before_json` | json | YES | — |  | — |
| `after_json` | json | NO | — |  | — |
| `created_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) |  / DEFAULT_GENERATED | 생성 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `PRIMARY` | 예 | history_id |
| `uq_context_history_version` | 예 | item_id, item_version |

| FK / CHECK | 정의 |
|---|---|
| `fk_context_history_item` | item_id → case_context_items.item_id; DELETE NO ACTION; UPDATE NO ACTION |

<a id="table-case_context_v2_history"></a>

### case_context_v2_history

보고서·이력 — 사실·업무 등 V2 자원 변경 이력

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 258행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `history_id` | bigint | NO | — | PRIMARY / auto_increment | — |
| `case_id` | varchar(32) | NO | — | idx_context_v2_history_case | 사건 연결 키 |
| `entity_type` | varchar(24) | NO | — | uq_context_v2_history_version | — |
| `entity_id` | varchar(64) | NO | — | uq_context_v2_history_version | — |
| `entity_version` | bigint | NO | — | uq_context_v2_history_version | — |
| `operation` | varchar(32) | NO | — |  | — |
| `actor_user_id` | varchar(64) | NO | — |  | — |
| `before_json` | json | YES | — |  | — |
| `after_json` | json | NO | — |  | — |
| `created_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) | idx_context_v2_history_case / DEFAULT_GENERATED | 생성 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `idx_context_v2_history_case` | 아니오 | case_id, created_at |
| `PRIMARY` | 예 | history_id |
| `uq_context_v2_history_version` | 예 | entity_type, entity_id, entity_version |

| FK / CHECK | 정의 |
|---|---|
| `fk_context_v2_history_case` | case_id → cases.case_id; DELETE CASCADE; UPDATE NO ACTION |

<a id="table-voice_sessions"></a>

### voice_sessions

음성·호환 — 음성 세션 상태·참여자 metadata; 원문 segment 저장 없음; API·bundle 호환용

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 0행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `session_id` | varchar(64) | NO | — | PRIMARY | — |
| `case_id` | varchar(32) | NO | — | idx_voice_sessions_case | 사건 연결 키 |
| `status` | enum('REQUESTED','ACTIVE','ENDED','FAILED') | NO | REQUESTED |  | 자원별 처리 상태 |
| `participants_json` | json | NO | — |  | — |
| `started_at` | datetime(6) | YES | — |  | — |
| `ended_at` | datetime(6) | YES | — |  | — |
| `created_at` | datetime(6) | NO | — | idx_voice_sessions_case | 생성 시각 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `idx_voice_sessions_case` | 아니오 | case_id, created_at |
| `PRIMARY` | 예 | session_id |

| FK / CHECK | 정의 |
|---|---|
| `fk_voice_sessions_case` | case_id → cases.case_id; DELETE NO ACTION; UPDATE NO ACTION |

<a id="table-schema_migrations"></a>

### schema_migrations

스키마 운영 — 적용 또는 검증된 기준선의 전체 migration 파일명

Engine: `InnoDB` · Collation: `utf8mb4_unicode_ci` · 31행

| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |
|---|---|---|---|---|---|
| `migration_name` | varchar(255) | NO | — | PRIMARY | 숫자 접두사가 아닌 전체 파일명이 식별자 |
| `applied_at` | datetime(6) | NO | CURRENT_TIMESTAMP(6) |  / DEFAULT_GENERATED | 적용/검증 기준선 등록 시각; 과거 실제 실행 시각으로 소급하지 않음 |

| 인덱스 | UNIQUE | 순서·컬럼 |
|---|---|---|
| `PRIMARY` | 예 | migration_name |

| FK / CHECK | 정의 |
|---|---|
| — | 없음 |

## 트리거 목록

| 이름 | 테이블 | 시점 | 작업 |
|---|---|---|---|
| `trg_actions_context_revision_delete` | `actions` | AFTER | DELETE |
| `trg_actions_context_revision_insert` | `actions` | AFTER | INSERT |
| `trg_actions_context_revision_update` | `actions` | AFTER | UPDATE |
| `trg_ai_suggestions_delete` | `case_ai_suggestions` | AFTER | DELETE |
| `trg_ai_suggestions_insert` | `case_ai_suggestions` | AFTER | INSERT |
| `trg_ai_suggestions_update` | `case_ai_suggestions` | AFTER | UPDATE |
| `trg_case_decisions_delete` | `case_decisions` | AFTER | DELETE |
| `trg_case_decisions_insert` | `case_decisions` | AFTER | INSERT |
| `trg_case_gaps_delete` | `case_gaps` | AFTER | DELETE |
| `trg_case_gaps_insert` | `case_gaps` | AFTER | INSERT |
| `trg_case_gaps_update` | `case_gaps` | AFTER | UPDATE |
| `trg_case_tasks_delete` | `case_tasks` | AFTER | DELETE |
| `trg_case_tasks_insert` | `case_tasks` | AFTER | INSERT |
| `trg_case_tasks_update` | `case_tasks` | AFTER | UPDATE |
| `trg_cases_context_revision_update` | `cases` | BEFORE | UPDATE |
| `trg_context_facts_v2_delete` | `case_context_facts_v2` | AFTER | DELETE |
| `trg_context_facts_v2_insert` | `case_context_facts_v2` | AFTER | INSERT |
| `trg_context_facts_v2_update` | `case_context_facts_v2` | AFTER | UPDATE |
| `trg_messages_context_revision_delete` | `messages` | AFTER | DELETE |
| `trg_messages_context_revision_insert` | `messages` | AFTER | INSERT |
| `trg_questions_context_revision_delete` | `customer_questions` | AFTER | DELETE |
| `trg_questions_context_revision_insert` | `customer_questions` | AFTER | INSERT |
| `trg_questions_context_revision_update` | `customer_questions` | AFTER | UPDATE |
| `trg_verifications_context_revision_delete` | `verification_tasks` | AFTER | DELETE |
| `trg_verifications_context_revision_insert` | `verification_tasks` | AFTER | INSERT |
| `trg_verifications_context_revision_update` | `verification_tasks` | AFTER | UPDATE |
