# 프론트엔드 우선 재설계 체크리스트

기준 브랜치: `v3.1-ham3`  
원칙: 프론트 구조를 먼저 확정하고, 이후 API 계약을 새로 작성한다.

## Phase 0 — 기준선 보존

- [x] `v3.1-ham2`를 기준으로 `v3.1-ham3` 생성
- [x] 기존 백엔드·기존 API 코드 보존
- [x] 기존 `ContextPanelV3`를 삭제하지 않고 legacy로 유지
- [ ] 기준 commit·현재 미커밋 변경사항을 사람이 확인

## Phase 1 — 빈 foundation 화면

- [x] 좌측·중앙·우측 큰 레이아웃 유지
- [x] 중앙에서 질문·답변·기관 확인·업무·보고서 카드를 숨김
- [x] 중앙에서 일반 메시지 말풍선 유지
- [x] 우측 패널을 제목 + 빈 영역으로 교체
- [x] 기존 빠른 질문/확인/조치 진입 버튼 숨김
- [ ] 브라우저에서 카드가 남아 있지 않은지 확인 — `HUMAN`
- [ ] 좌측·중앙·우측 너비와 접기 동작 확인 — `HUMAN`

## Phase 2 — 프론트 화면 설계

- [ ] 새 좌측 탐색 정보 확정 — `HUMAN`
- [ ] 중앙 메시지 표현과 입력 대상 확정 — `HUMAN`
- [ ] 우측 패널 섹션 수·순서·제목 확정 — `HUMAN`
- [ ] 로딩/빈 상태/실패/갱신 대기 화면 확정 — `HUMAN`
- [ ] 카드 대신 사용할 새 표시 단위 확정 — `HUMAN`

## Phase 3 — View Model 확정

- [ ] `02_FRONTEND_VIEW_MODEL_DRAFT.md` 검토
- [ ] 표시 문장 단위 확정
- [ ] status/evidence/visibility 필드 확정
- [ ] mock JSON fixture 작성
- [ ] 프론트 컴포넌트가 mock만으로 렌더링되는지 확인

## Phase 4 — 새 API 계약

- [ ] View Model을 API DTO로 변환
- [ ] 서버가 제공해야 할 revision 정의
- [ ] LLM 전체 문장 `display_text` 계약 정의
- [ ] 권한·고객 공개 범위 정의
- [ ] provider 실패·재시도 계약 정의
- [ ] 기존 API와 새 API의 공존 기간 결정 — `HUMAN`

## Phase 5 — 연결 및 제거

- [ ] mock repository를 실제 API repository로 교체
- [ ] 실제 projection revision 갱신 확인
- [ ] 새로고침·재접속 복원 확인
- [ ] 고객/은행 visibility 확인
- [ ] 기존 카드 코드 사용처 확인
- [ ] 사람 승인 후 legacy UI 제거 여부 결정 — `HUMAN`

## 완료 판정

- [ ] 백엔드를 수정하지 않고 새 foundation 화면이 동작한다.
- [ ] 화면에는 새 계약 이전의 카드가 표시되지 않는다.
- [ ] 프론트 View Model이 사람 승인되었다.
- [ ] 새 API 계약이 문서화되었다.
- [ ] 실제 API 연결 후에도 프론트가 문장을 조립하지 않는다.
