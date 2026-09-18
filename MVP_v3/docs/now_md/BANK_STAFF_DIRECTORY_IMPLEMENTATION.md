# 은행 담당자 관리 구현

## 범위

홈 화면의 `start-analysis-button` 바로 아래에 `은행 담당자 관리` 버튼을 제공하고, 은행 전역 담당자 디렉터리를 조회·등록·수정·소프트 삭제할 수 있는 드로어를 추가했습니다. Case Participant 기능과 분리되어 있으며 고객 화면에는 노출되지 않습니다.

## API와 저장

- `GET/POST /api/bank/staff`
- `PATCH/DELETE /api/bank/staff/{staff_id}`
- 마이그레이션: `backend/migrations/020_bank_staff_directory.sql`
- 삭제는 `deleted_at`을 기록하는 soft delete입니다.
- 상태 색상은 GREEN, BLUE, YELLOW, ORANGE, RED, PURPLE, GRAY 토큰만 허용합니다.

프론트는 서버 응답을 받은 뒤 목록을 갱신하며, 로딩·오류·빈 상태와 삭제 확인을 표시합니다. AI API와 기존 사건 참여자 계약은 변경하지 않았습니다.

## 검증

- `MVP_v3/frontend`: `npm.cmd run typecheck` 통과
- `MVP_v3`: `python -m compileall -q backend/general_api backend/contracts` 통과

운영 DB 반영은 배포 환경에서 migration runner로 020번을 적용해야 합니다.
