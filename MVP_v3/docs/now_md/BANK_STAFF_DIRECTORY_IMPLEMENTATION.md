# 은행 담당자 관리 구현

## 범위

홈 화면의 `start-analysis-button` 바로 아래에 `은행 담당자 관리` 버튼을 제공하고, 은행 전역 담당자 디렉터리를 조회·등록·수정·소프트 삭제할 수 있는 드로어를 추가했습니다. Case Participant 기능과 분리되어 있으며 고객 화면에는 노출되지 않습니다.

## API와 저장

- `GET/POST /api/bank/staff`
- `PATCH/DELETE /api/bank/staff/{staff_id}`
- 마이그레이션: `backend/migrations/staff/020_bank_staff_directory.sql`
- 삭제는 `deleted_at`을 기록하는 soft delete입니다.
- 상태 색상은 GREEN, BLUE, YELLOW, ORANGE, RED, PURPLE, GRAY 토큰만 허용합니다.
- 전사 담당자 화면에서는 Case별 역할을 배정하지 않습니다. Case별 배정 역할은 `case_members.assignment_role`에 저장합니다.
- `assignment_eligible`로 향후 Case 자동 배정 대상 여부를 명시합니다.

프론트는 목록을 기본으로 열고 `담당자 추가` 또는 `수정`을 눌렀을 때만 입력 화면으로 전환합니다. 서버 응답을 받은 뒤 목록을 갱신하며, 로딩·오류·빈 상태와 삭제 확인을 표시합니다. AI API는 변경하지 않고, 사건 참여자 계약에는 케이스별 `assignment_role`만 추가합니다.

## 검증

- `MVP_v3/frontend`: `npm.cmd run typecheck`, `npm.cmd run build` 통과
- `MVP_v3`: `python -m compileall -q backend/general_api backend/contracts` 통과
- General API에서 목록·등록·수정·소프트 삭제를 실제로 확인했습니다.

운영 DB 반영은 배포 환경에서 migration runner로 020번과 022번을 순서대로 적용해야 합니다. 기존 DB에 오래된 migration 충돌이 있으면 `--only 022_case_member_assignment_roles.sql`처럼 케이스 역할 migration을 검토 후 적용합니다.
