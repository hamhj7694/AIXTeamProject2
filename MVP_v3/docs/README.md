# MVP v3 문서 안내

사람과 Codex는 [`CURRENT_STATUS.md`](CURRENT_STATUS.md)를 먼저 읽는다. 이 폴더에는 현재 구현을 운영·변경할 때 계속 필요한 최신 상태와 계약만 둔다.

| 문서 | 역할 |
|---|---|
| [`CURRENT_STATUS.md`](CURRENT_STATUS.md) | 현재 구현, 미완료 범위, 우선순위, 최신 검증 |
| [`DB_CATALOG.md`](../database/DB_CATALOG.md) | 전체 DB 엔티티·테이블·행 수·컬럼·PK/FK·제약조건·트리거 표 |
| [`DB_USAGE_AUDIT.md`](../database/DB_USAGE_AUDIT.md) | 테이블·컬럼 실제 사용처 분류와 이번 단계의 API 제거·전환 판정 |
| [`DB 운영 안내`](../database/README.md) | 신규 초기화·읽기 전용 점검·백업/복원·스키마 정상화 |
| [`엔티티별 migrations`](../backend/migrations/README.md) | 엔티티별 migration 책임·실행 순서·과거 이력 취급 |
| [`04_PRIVACY_SAFE_SIGNAL_FLOW.md`](04_PRIVACY_SAFE_SIGNAL_FLOW.md) | 데모 원문 보관과 AI 비접근·privacy-safe 저장 경계 |
| [`07_CUSTOMER_PROGRESS_AND_AI.md`](07_CUSTOMER_PROGRESS_AND_AI.md) | 고객 공개 진행 상태, 확인 요청, AI 공개 범위 |
| [`09_CASE_CONTEXT_DATA_CONTRACT.md`](09_CASE_CONTEXT_DATA_CONTRACT.md) | Fact·Gap·Suggestion·Task·Decision 및 비벡터 Case-local 검색 계약 |
| [`10_FINAL_CASE_REPORT_CONTRACT.md`](10_FINAL_CASE_REPORT_CONTRACT.md) | 사건 종결 AI 보고서 계약 |
| [`33_ANALYSIS_ENVELOPE_FREEZE_CONTRACT.md`](33_ANALYSIS_ENVELOPE_FREEZE_CONTRACT.md) | 원문 보관·AI 비접근형 Analysis Envelope와 새 통화 분석 병합 기준선 |
| [`34_ANALYSIS_ENVELOPE_INTEGRATION_BACKLOG.md`](34_ANALYSIS_ENVELOPE_INTEGRATION_BACKLOG.md) | 실제 외부 연동을 제외한 Envelope 데모 완성·GitHub 보호 후속 순서 |

구현 전 계획, 회의록, 일회성 감사, 마감 체크리스트, 구현 완료 보고서와 프롬프트 요청서는 현재 상태에 필요한 결론만 흡수한 뒤 유지하지 않는다. 과거 이력이 필요하면 Git history를 사용한다.
