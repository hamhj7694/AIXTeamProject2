# 전체 작업 카탈로그 · 3인 책임 기준

> 기준일: 2026-09-02. 실제 코드에서 확인된 남은 작업만 관리한다.
> 과거 구현 기여는 개인 TODO의 완료 이력에 보존하고, 아래 담당은 향후 책임자다.

## 1. 현재 기준선

| ID | 기능 | 코드 기준 상태 | 향후 책임 |
|---|---|---|---|
| AI-01~04 | Full/Window 분석, Feature, Risk | DONE, 재검증 필요 | B |
| BE-01 | `POST /api/cases/analyze` | DONE | A |
| BE-02 | `GET /api/cases` | DONE | A |
| BE-03 | Case 상세·초기 LIVE Report 조회 | DONE | A |
| DB-01 | Core Case/Diagnosis/Report Migration | DONE, 실제 환경 재검증 필요 | A |
| FE-01~03 | 진단·목록·상세 UI/API | MOSTLY_DONE | C |
| FE-04~06 | Customer·Bank·Verification UI | MOCK/PARTIAL | C |
| BE-04 이후 | Message·Verification·Action·상태 갱신 | TODO | A |
| AI-05 이후 | Brief update·Agent·RAG·Voice AI | TODO | B |
| RT/INT | Realtime·전체 E2E·Docker | TODO | C |

## 2. P0 — 기준선·Contract 고정

| ID | 작업 | 담당 | 선행 | 완료 기준 |
|---|---|---|---|---|
| A-00 | MySQL Migration·Repository 재검증 | A | 없음 | 실제 적용, CRUD, rollback test |
| A-01 | Case List/Get/Patch Public DTO·Enum | A | C 요구 Review | Pydantic DTO와 Contract test |
| B-00 | ML bundle·Feature·Risk 인계 검증 | B | 없음 | hash·output·fixture test |
| B-01 | AI Internal DTO/JSON Schema 정합화 | B | A Review | 정상·부분실패 Example·test |
| C-00 | 화면별 API/Mock/localStorage Data Source Map | C | 없음 | Route별 출처와 교체 순서 문서화 |
| C-01 | Analyze/List/Detail Adapter 회귀 | C | A-01 | Loading/Error/NO_CASE 포함 검증 |

## 3. P1 — 핵심 MVP

| ID | 작업 | 담당 | 선행 | 완료 기준 |
|---|---|---|---|---|
| A-10 | Case PATCH·상태전이·Version Conflict | A | A-01 | 허용 전이와 409 test |
| A-11 | Message API·저장 | A | A-00 | create/list transaction test |
| A-12 | Event/Timeline append·cursor | A | A-00 | actor/timestamp/payload와 cursor test |
| A-13 | Verification/Action API | A | A-10 | 생성·응답·상태·history test |
| B-10 | P0/P1/P2 Question Planner | B | A-01 | priority/target/execution schema와 guardrail |
| B-11 | 고객 자유답변 구조화 | B | B-10 | Case patch output·evaluation |
| B-12 | Customer/Bank/Verification Agent | B | B-10/11 | 근거·실패를 포함한 Contract test |
| B-13 | Initial/LIVE Brief update | B | Event Contract | Section 단위 output test |
| C-10 | Customer/Bank Message·상태 연결 | C | A-11/12 | 동일 Case 양 화면 반영 |
| C-11 | Verification·FDS·ASAP Mock Adapter | C | A-13 | Mock 경계와 Scenario fixture |
| C-12 | SSE/WebSocket·재접속 | C | A-12 | 중복·순서·재접속 E2E |
| C-13 | Human Takeover/Resume AI | C | A-10/12 | 서버 상태 기반 양 화면 동기화 |

## 4. P2/P3 — 안정화·확장

| ID | 작업 | 담당 | 선행 | 완료 기준 |
|---|---|---|---|---|
| A-20 | 인증·권한·공통 오류·관측 | A | P1 | 역할/오류/로그 test |
| B-20 | Agent Orchestrator | B | B-12/13 | 결정론적 routing·부분실패 test |
| B-21 | RAG Pipeline·Evaluation | B | Corpus 결정 | 출처·최신성·환각 평가 |
| B-22 | Voice/STT Intelligence | B | Voice Contract | Partial/Final·중복 test |
| C-20 | Browser Full Demo E2E | C | P1 | 핵심 Scenario 자동화 |
| C-21 | Docker Compose·배포 | C | A/B 실행 고정 | 4개 서비스 cold start·health |

## 5. 의존성

```text
B가 새 Case Field 필요
→ B 요구·Schema·Example
→ A DB/Service/API
→ C Adapter/UI

C가 새 Event 필요
→ C UI 갱신 요구
→ A/B/C Event Contract
→ A/B Producer
→ A 저장·발행
→ C 구독
```

## 6. DONE 공통 기준

- [ ] Schema와 Example 확정
- [ ] 제공자·소비자 Contract Test
- [ ] 정상·오류·Timeout/부분실패 중 해당 테스트
- [ ] Secret·민감정보·로그 점검
- [ ] 실제 또는 Fixture 연동 E2E
- [ ] 개인 TODO에 변경 파일·테스트·다음 작업 기록
