# 수동 되돌리기 SQL — 엔티티별 분류

정방향 manifest에 포함하지 않는다. 이름이 같은 정방향 SQL과 동일한 엔티티 폴더에 분류했다.

| 엔티티 | 파일 |
|---|---|
| 복수 엔티티 공통 | [014_case_context_v2_foundation.sql](shared/014_case_context_v2_foundation.sql) |
| 대화·질문 | [015_context_panel_v3.sql](conversations/015_context_panel_v3.sql) |
| 사건 | [016_case_name.sql](cases/016_case_name.sql) |
| 구조화 정황 | [017_structured_context_resources.sql](analysis/017_structured_context_resources.sql) |
| 구조화 관찰 | [019_context_observations.sql](analysis/019_context_observations.sql) |
| 직원 명부 | [020_bank_staff_directory.sql](staff/020_bank_staff_directory.sql) |
| 사건 참여자 | [022_case_member_assignment_roles.sql](members/022_case_member_assignment_roles.sql) |

이 파일들은 기존 이력 보존용이며 최신 DB에서 안전한 일괄 되돌리기를 보장하지 않는다. 테이블·컬럼 삭제로 데이터가 유실될 수 있다. 복원 가능한 백업과 후속 migration/FK/트리거 의존성을 확인한 뒤 명시적으로 선택해서 사용한다. 모든 migration에 rollback이 있는 것은 아니며, 자동 역순 실행 도구는 제공하지 않는다.
