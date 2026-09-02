# eom TODO — A Backend & Case Platform

> 아래 체크리스트는 앞으로의 책임 기준이다. 과거 AI/Vertical Slice 기여는 하단 완료 이력에 보존한다.

## P0 — 지금 바로

- [ ] 현재 MySQL Migration과 실제 사용 Table 확인
- [ ] `CASE_REPOSITORY=memory/mysql` 전환 재검증
- [ ] MySQL Repository Create/List/Get transaction test
- [ ] DB 실패 시 rollback 자동화 test
- [ ] Case List/Get 공개 응답 DTO 확정
- [ ] Case status/mode/risk/error enum 정리
- [ ] `PATCH /api/cases/{case_id}` 상태전이 요구 정리
- [ ] C에게 Case 화면 필수 필드 Review 요청

## P1 — 핵심 MVP

- [ ] Case PATCH·허용 상태전이·409 Version Conflict
- [ ] Message migration·Repository·create/list API
- [ ] Event/Timeline append·list·cursor API
- [ ] Event actor·timestamp·payload·version Contract
- [ ] Verification Task migration·API
- [ ] 외부 Verification 응답 저장·상태 변경
- [ ] Action/History API
- [ ] Human Takeover/Resume 상태 저장 API
- [ ] 저장 성공 후 Event 발행 경계 제공

## P2 — 안정화

- [ ] 역할/권한 검증
- [ ] Request ID·구조화 로그·민감정보 제거
- [ ] DB 재시도·Pool 종료·장애 처리
- [ ] 공통 Error/Validation Envelope 확대
- [ ] Repository·Service·API 통합 test

## 다른 담당자에게 필요한 것

- B=lee: 질문·자유답변·Agent output의 의미, Schema, Example
- C=ham: 화면에 필요한 Case/Event field와 Realtime 소비 요구

## 건드리지 않기

- [ ] AI Prompt·Agent 내부 로직을 직접 수정하지 않는다.
- [ ] Frontend 화면 문제는 C에게 재현 자료와 함께 전달한다.
- [ ] 공용 Contract는 B/C 영향 확인 없이 깨뜨리지 않는다.

## 기존 완료 이력 — 과거 구현 기여

- [x] WindowAI·Full Context LLM·Feature·Risk/Fusion 초기 구현
- [x] FastAPI 2계층과 Diagnosis→Case 생성 흐름 초기 구현
- [x] Core Case/Diagnosis/LIVE Report Migration과 MySQL Repository 초기 구현
- [x] Analyze/List/Get/LIVE Report와 Frontend 프록시 연결 초기 구현
- 기록된 과거 실행에서는 Python test·HTTP E2E·Frontend build가 통과했다.
- 2026-09-02 감사 환경에서는 공개 Contract test 4건만 재통과했고, 일부 Python test와 Frontend build는 로컬 의존성/실행환경 제한으로 재검증하지 못했다.

## 작업 로그 템플릿

### YYYY-MM-DD — TASK-ID

- 목표:
- 변경 파일:
- 테스트 결과:
- 미검증/Blocker:
- 협업 요청:
- 다음 작업:
