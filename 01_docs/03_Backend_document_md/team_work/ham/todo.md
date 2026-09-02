# ham TODO — C Realtime & Service Integration

## P0 — 지금 바로

- [ ] Frontend Route별 Data Source 확인
- [ ] 실제 API 사용 화면과 Mock 화면 구분
- [ ] localStorage·Browser event 사용 위치 목록화
- [ ] `VITE_API_BASE_URL`과 Vite proxy 확인
- [ ] Analyze/List/Detail Loading·Error·NO_CASE 회귀
- [ ] Manager Room API Adapter 경계 설계
- [ ] Customer/Bank/Verification Mock 교체 순서 작성
- [ ] SSE vs WebSocket 요구사항과 선택 기준 정리

## P1 — 핵심 MVP

- [ ] Customer 메시지·답변을 Backend API에 저장
- [ ] 동일 Case 답변을 Bank 화면에 반영
- [ ] Manager Room Case Header·Brief·Message 연결
- [ ] Timeline Event append UI
- [ ] Verification Task·응답 Mock Adapter 연결
- [ ] FDS Mock Adapter와 `MVP Mock` 표시 유지
- [ ] ASAP Mock 범위·Fixture 정의
- [ ] Human Takeover/Resume AI 서버 상태 연결
- [ ] SSE/WebSocket 구독·재접속·중복 처리
- [ ] Customer↔Bank 핵심 Browser E2E

## P2 — 안정화

- [ ] 통합 Error·Loading·Empty·Retry UI
- [ ] Event 순서 역전·중복·누락 test
- [ ] Stream 재연결 후 최신 State 복구
- [ ] Frontend Adapter Contract test
- [ ] Dockerfile·Compose·환경변수 정리
- [ ] Frontend+General API+AI API+MySQL cold start
- [ ] Demo Scenario Smoke Test

## P3 — 확장

- [ ] Voice Session·STT UI 연결
- [ ] Transcript append-only Realtime
- [ ] 배포 Health Check·운영 환경 설정

## 다른 담당자에게 필요한 것

- A=eom: Case/Message/Event/Verification/Action Public API와 Event stream
- B=lee: Agent/Question/Brief output Schema와 안전 문구

## 건드리지 않기

- [ ] DB Schema·Migration을 직접 변경하지 않는다.
- [ ] AI Prompt·Agent 내부 로직을 직접 수정하지 않는다.
- [ ] Mock 데이터를 실제 금융기관 응답처럼 표시하지 않는다.

## 현재 확인된 Mock 경계

- Manager Room: `features/manager-room/data/managerRoomMock.ts`
- Customer 답변·Takeover: localStorage와 custom browser event
- Verification: Frontend local state
- FDS·STT Evidence: Manager Room fixture
- 실제 SSE/WebSocket·ASAP Adapter: 없음

## 작업 로그 템플릿

### YYYY-MM-DD — TASK-ID

- 목표:
- 변경 파일:
- 테스트 결과:
- Mock/실제 경계:
- 협업 요청:
- 다음 작업:
