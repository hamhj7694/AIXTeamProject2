# DB 마이그레이션 — 엔티티별 안내

General API가 소유하는 MySQL 8.0 서비스 DB의 변경 이력이다. **정방향 SQL 29개와 rollback SQL 7개를 엔티티별 하위 폴더로 분류했다.** 실행 순서는 [manifest.json](manifest.json)에 명시한 전역 순서이며, 현재 manifest와 실제 정방향 SQL 수가 일치한다. DB 적용 이력은 경로가 아닌 기존 전체 파일명으로 유지한다. 동일 접두사 `009`의 두 파일도 각각 독립적인 migration이다.

## 실제 폴더 구조

| 폴더 | 담당 엔티티 / 범위 |
|---|---|
| `cases/` | 사건 이름·버전 |
| `analysis/` | Atom·Relation·Signal·Observation |
| `staff/` | 은행 직원 명부·데모 직원·역할 제약 |
| `members/` | 사건 참여자의 배정 역할 |
| `conversations/` | 메시지 중복 방지·고객 질문·정보 추출 작업 |
| `transactions/` | 개별 거래 내역 |
| `facts/` | 사실과 고객 질문의 근거 연결 |
| `actions/` | 조치 계약 필드 |
| `context/` | 화면 편집 항목과 이력 |
| `reports/` | 보고서와 보고서 섹션 |
| `attachments/` | 첨부파일 기능 생성 및 안전한 폐기 |
| `voice/` | 음성 세션·호환 구조 |
| `shared/` | 여러 엔티티를 동시에 변경하는 기존 통합 migration |
| `rollback/<동일 엔티티>/` | 수동 복구용 SQL 7개, 자동 실행 제외 |

이미 적용한 SQL을 분할하거나 재작성하지 않도록 `shared/`는 원래 SQL 전체를 보존한다. 이동 전후 32개 SQL의 SHA-256 일치를 확인했다. 경로 변경 시 파일명·SQL 내용은 유지하고 manifest와 참조 경로를 함께 갱신한다.

- [전체 DB·컬럼·관계·현재 행 수 표](../../database/DB_CATALOG.md)
- [DB 사용처·중복·제거 감사](../../database/DB_USAGE_AUDIT.md)
- [프론트·백엔드·DB 계약 대조](../../database/API_CONTRACT_AUDIT.md)
- [초기화·백업·정상화·점검 명령](../../database/README.md)
- [최신 상태와 미해결 데이터/금액 문제](../../docs/CURRENT_STATUS.md)

## 엔티티별 저장 책임

| 엔티티 | 테이블 | 관련 migration |
|---|---|---|
| 사건·분석 | cases, case_inputs, analysis_segments, context_features | 001, 003, 006, 009_mysql_parity_workflow, 013, 016 |
| 구조화 정황 | case_semantic_atoms, case_semantic_relations, case_context_signals, case_context_observations | 017, 019 |
| 직원·참여자 | bank_staff_directory, case_members, case_presence | 008, 020, 022, 023, 024 |
| 대화·고객 질문 | messages, customer_questions, message_context_extractions | 004, 008, 009_mysql_parity_workflow, 011, 015 |
| 거래 | case_transactions | 021_create_case_transactions |
| 사실·확인 | case_facts(027/028에서 폐기), verification_tasks, case_context_facts_v2, case_gaps | 005, 009_mysql_parity_workflow, 010, 014, 027, 028 |
| 조치·업무·결정 | actions, case_ai_suggestions, case_tasks, case_decisions | 005, 014, 018 |
| 화면·캐시 | case_context_items, case_context_projections, personal_notes | 009_mysql_parity_workflow, 012, 013 |
| 보고서·감사 | case_reports, case_report_sections, case_events, case_context_item_history, case_context_v2_history | 001, 002, 004, 012, 014 |
| 음성·호환 | voice_sessions | 007, 025 |
| 스키마 운영 | schema_migrations | runner 생성; 전체 파일명 단위 적용 이력 |

## 사건·분석·구조화 정황

| 파일 | 변경 | 보존 원칙 |
|---|---|---|
| [001_core_case_diagnosis.sql](shared/001_core_case_diagnosis.sql) | Case, 입력 원장, 분석 구간, 수치 피처, 이벤트 | 데모 원문은 `case_inputs`에 보관하고 지원 AI에는 재전달하지 않음 |
| [003_expand_risk_score_precision.sql](shared/003_expand_risk_score_precision.sql) | 위험도 DECIMAL(9,6) | 점수 의미 변경 없음 |
| [006_case_version.sql](cases/006_case_version.sql) | Case version | 수정 충돌 확인용 |
| [016_case_name.sql](cases/016_case_name.sql) | 사용자 Case 이름 | 분석 요약과 별개 |
| [017_structured_context_resources.sql](analysis/017_structured_context_resources.sql) | Atom·Relation·Signal 저장 | Case 내부 ID와 역할·출처 metadata 유지 |
| [019_context_observations.sql](analysis/019_context_observations.sql) | 미분류 구조화 관찰 | 분류되지 않았다고 원문을 저장하지 않음 |

## 직원·참여자

| 파일 | 변경 | 보존 원칙 |
|---|---|---|
| [008_collaboration_channels.sql](shared/008_collaboration_channels.sql) | 채널, 담당자, 접속 상태 | 권한·배정·접속 상태를 구별 |
| [020_bank_staff_directory.sql](staff/020_bank_staff_directory.sql) | 직원 명부와 배정 직무 | 명부 역할 5종과 직원 편집 정보 보존 |
| [022_case_member_assignment_roles.sql](members/022_case_member_assignment_roles.sql) | 사건별 assignment_role | 권한 role과 별개. 기타 열람자 코드는 명부 OTHER_VIEWER / 멤버 VIEWER로 서로 다름 |
| [023_bank_staff_demo_seed.sql](staff/023_bank_staff_demo_seed.sql) | 고정 ID 데모 직원 2명 | INSERT IGNORE로 기존 직원 편집을 덮어쓰지 않음 |
| [024_bank_staff_role_schema_alignment.sql](staff/024_bank_staff_role_schema_alignment.sql) | 과거 VARCHAR(24)·3종 CHECK를 VARCHAR(32)·5종으로 확장 | 직원의 실제 배정 역할 값은 변경하지 않음 |

## 대화·고객 질문·기존 사실

| 파일 | 변경 | 보존 원칙 |
|---|---|---|
| [004_case_messages_and_event_actor.sql](shared/004_case_messages_and_event_actor.sql) | 메시지, 이벤트 actor | 고객/직원/AI 구별 |
| [009_mysql_parity_workflow.sql](shared/009_mysql_parity_workflow.sql) | 피해 요약, 메시지 공개 범위, 질문, legacy Fact, 개인 메모 | 기존 테이블 하위 호환 유지 |
| [010_case_fact_question_link.sql](facts/010_case_fact_question_link.sql) | legacy Fact와 질문 연결 | 근거 연결 보존 |
| [011_message_idempotency.sql](conversations/011_message_idempotency.sql) | Case+client_request_id UNIQUE | 재전송과 별개 메시지를 구분 |
| [015_context_panel_v3.sql](conversations/015_context_panel_v3.sql) | 구조화 답변·버전, durable 추출 job | 사용자 답변을 자동 확정 사실로 승격하지 않음 |

## 거래·사실·확인·업무

| 파일 | 변경 | 보존 원칙 |
|---|---|---|
| [021_create_case_transactions.sql](transactions/021_create_case_transactions.sql) | 개별 거래 원장 | 금액 후보를 자동 거래 생성/확정하지 않음. 실제 은행 연동 아님 |
| [005_verification_actions.sql](shared/005_verification_actions.sql) | 확인 업무·조치 저널 | 외부 지급정지/신고 실행과 구분 |
| [014_case_context_v2_foundation.sql](shared/014_case_context_v2_foundation.sql) | Fact·Gap·Suggestion·Task·Decision·이력 | 확인자·시각, PROPOSED/CONFIRMED 경계 보존 |
| [027_migrate_legacy_case_facts_to_v2.sql](facts/027_migrate_legacy_case_facts_to_v2.sql) | 지원되는 legacy Fact를 deterministic ID로 V2에 복사 | 값·근거·source/status를 명시적 매핑하고 재실행 가능 |
| [028_retire_legacy_case_facts.sql](facts/028_retire_legacy_case_facts.sql) | legacy `case_facts` 행을 검증 후 정리하고 물리 테이블 DROP | 미지원 행이 남아 있으면 fail-closed |
| [018_action_contract_fields.sql](actions/018_action_contract_fields.sql) | 조치 제목·버전·수정자·공개 범위 | 기존 note 유지, 과거 updated_at은 created_at으로 보완 |

거래 금액, 고객 송금 진술, 요구 금액, Case 요약 피해금액은 서로 다른 개념이다. 테이블 생성은 누락된 구조를 해결하지만 금액 후보 중첩·합계 알고리즘까지 수정하지는 않는다.

## 화면·캐시·보고서·첨부·음성

| 파일 | 변경 | 보존 원칙 |
|---|---|---|
| [002_initial_live_report.sql](reports/002_initial_live_report.sql) | 보고서 원장·섹션 | Case별 LIVE/FINAL 분리 |
| [007_voice_sessions.sql](voice/007_voice_sessions.sql) | 음성 세션 호환 구조 | 다중 transcript segment는 025에서 폐기; 분석 입력 원문은 `case_inputs` 사용 |
| [025_retire_transcript_storage.sql](voice/025_retire_transcript_storage.sql) | 레거시 원문 저장 테이블 제거 | 행이 0건일 때만 삭제하고, 데이터가 있으면 migration을 중단 |
| [009_case_attachments.sql](attachments/009_case_attachments.sql) | (과거) 파일 metadata·메시지 연결 | 026에서 빈 테이블만 안전하게 폐기 |
| [026_retire_attachments.sql](attachments/026_retire_attachments.sql) | 데모 범위 제외. 두 첨부 테이블이 비어 있을 때만 DROP | 행이 있으면 fail-closed로 중단 |
| [012_context_items.sql](context/012_context_items.sql) | 직원 표시 편집본·이력 | 직원 편집을 AI로 덮어쓰지 않음 |
| [013_context_projection_revision.sql](shared/013_context_projection_revision.sql) | revision·lease·마지막 성공 캐시·트리거 | 캐시와 원본 사실을 구분 |

## 실행·재실행·과거 이력

저장소 루트 기준:

```powershell
MVP_v3/.venv/Scripts/python.exe MVP_v3/backend/scripts/apply_migrations.py
MVP_v3/.venv/Scripts/python.exe MVP_v3/backend/scripts/build_schema_bootstrap.py
```

- 정상 이력이 있는 DB는 runner가 적용한 파일을 건너뛴다. runner와 normalizer는 동일 DB의 migration 잠금을 공유한다.
- MySQL DDL은 자동 커밋된다. rollback만으로 스키마를 되돌릴 수 없다. 기존 DB 변경 전 백업·복원 검증과 General API 일시 중지가 필요하다.
- 2026-09-21 로컬 `csr`은 전체 구조·제약·트리거 대조와 백업 복원 검증 후 004~011의 미기록 9건을 기준선으로 기록했다. SQL 재실행이나 업무 데이터 변경은 하지 않았다. 등록 시각은 과거 실행 시각으로 소급하지 않았다.
- `021_bank_staff_assignment_fields.sql`은 과거 브랜치 이력이다. 원본 파일이 현재 브랜치에 없으므로 가짜 파일을 만들거나 이름을 바꾸지 않는다. 현재 요구 구조는 020+024로 검증한다.
- `015_case_number_sequence.sql`과 `case_number_sequences`는 allocator 변경 revert 이후 현재 코드에 없다. 예전 문서의 생성 지시를 제거했다. 현재 MAX+1 방식의 동시 생성 충돌 개선은 별도 업무 로직 작업이다.
- `rollback/`은 runner 검색 대상이 아니다. 데이터가 있는 상태에서 파괴적 rollback을 자동 실행하지 않는다.
- 다중 transcript segment 저장 경로는 폐기했다. 과거 transcript 등록/조회 URL은 호환을 위해 410 `TRANSCRIPT_STORAGE_DISABLED`를 반환하지만 요청 본문을 파싱하거나 저장하지 않는다. 데모 분석 요청의 단일 원문은 `case_inputs.input_text`에 보관하며 최초 분석 결과 화면 외 일반 Case read/list/bundle·Case Copilot·Context AI 입력에는 포함하지 않는다. 현재 `csr`의 `transcript_segments` 행 수가 0일 때만 025 migration이 테이블을 제거하며, 1건이라도 있으면 삭제하지 않고 수동 검토를 요구한다.
- `messages.attachments_json`과 응답의 `attachments: []`는 첨부파일 기능이 아니라 구버전 클라이언트 계약을 위한 빈 호환 필드다. 모든 클라이언트 전환·접근 로그·계약 테스트가 완료된 뒤 마지막 단계에서 컬럼·요청 필드·응답 필드를 함께 제거한다. 현재는 실제 첨부 데이터를 저장하지 않는다.
- manifest에 없는 정방향 SQL, 중복 파일명, 누락 파일, 순서 변경, rollback 포함은 실행 전에 오류로 차단한다. `--only`에는 폴더 없는 전체 파일명을 사용한다.
- 신규 변경은 해당 엔티티 폴더에 새 번호 SQL로 추가하고 `manifest.json` 끝에 등록한 후 `build_schema_bootstrap.py --write`로 파생 초기화 파일을 갱신한다. 두 초기화 경로의 일치 테스트를 통과시킨다.
