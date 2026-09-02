# 작업 매핑 문서

> 기준일: 2026-09-02
> 상세 실행 Backlog는 `team_work/00_task_catalog.md`, 개인 순서와 체크리스트는 `team_work/{eom|lee|ham}`을 따른다.

## 1. 책임 코드

```text
A = eom = Backend / Case / MySQL / Public API
B = lee = AI / Agent / RAG / AI Internal Contract
C = ham = Frontend / Realtime / Integration / E2E / Docker
```

과거 구현자는 Git과 개인 완료 이력에 보존한다. 아래 담당은 향후 유지·추가개발 책임자다.

## 2. 현재 구현 매핑

| ID | 기능 | 실제 상태 | 과거 주요 기여 | 향후 책임 |
|---|---|---|---|---|
| FE-01 | 통화 텍스트 진단 | 대부분 완료 | eom/lee | C |
| FE-02 | Case List | 대부분 완료, API 사용 | eom/lee | C |
| FE-03 | Case Detail/Role Entry | 대부분 완료, API 사용 | eom/lee | C |
| FE-04 | Customer Room | 부분 구현·Mock/localStorage | 기존 Frontend | C |
| FE-05 | Bank Manager Room | Mock UI | ham | C |
| FE-06 | Verification | Frontend Mock | 기존 Frontend | C |
| BE-01 | Analyze API | 완료 | eom/lee | A |
| BE-02 | Case List API | 완료 | eom | A |
| BE-03 | Case Detail/LIVE Report | 완료 | eom | A |
| DB-01 | Core Case/Diagnosis/Report Migration | 완료·재검증 필요 | eom/lee | A |
| AI-01~04 | Full/Window/Feature/Risk | 완료·재검증 필요 | eom | B |
| BE-04 이후 | Message/Verification/Action/상태 갱신 | 시작 전 | - | A |
| AI-05 이후 | Brief update/Question/Agent/RAG/Voice | 설계·Fixture 일부 | eom/lee | B |
| RT-01 이후 | SSE/WebSocket·실시간 동기화 | 시작 전 | - | C |
| INT | 전체 Browser E2E·Docker·배포 | 시작 전 | ham/팀 | C |

## 3. 기능별 향후 책임

| 영역 | Provider | Consumer/Reviewer | 핵심 결과물 |
|---|---|---|---|
| Case·Message·Verification·Action API | A | C, 필요 시 B | Public DTO, Service, Repository, Test |
| MySQL·Migration·Transaction | A | B/C 영향 Review | Schema, Migration, Rollback Test |
| ML·Context·Risk | B | A | AI Internal DTO, Evidence, Evaluation |
| Question·Agent·Brief·RAG | B | A/C | Schema, Fixture, Prompt/Model Version |
| Frontend API Adapter | C | A | 화면별 Server State와 Error 처리 |
| Realtime | A 저장·발행 / C 구독 | B producer Review | Event Contract, Cursor, Reconnect |
| Mock FDS·ASAP·Verification | C | A/B | 명시적 Adapter·Scenario Fixture |
| E2E·Docker·배포 | C | A/B | Browser Test, Compose, Health Check |

## 4. 의존성

```text
B가 새 Case Field 필요
→ B 의미·Schema·Example
→ A DB/Service/Public API
→ C Adapter/UI

C가 새 Event 필요
→ C UI 갱신 요구
→ A/B/C Contract 합의
→ A/B Producer
→ A 저장·발행
→ C 구독·재접속
```

## 5. Task 작성 필수 항목

- 작업명, 현재 상태, 필요 이유, 담당자
- 선행·후속 작업, 관련 파일
- 공용 Contract 영향 여부
- 구현 방법, 완료 기준, 테스트 방법
- 협업 필요 여부, P0~P3 우선순위

## 6. Definition of Done

- [ ] 실제 코드 구현
- [ ] 입력·출력 Schema와 Example
- [ ] Error/Timeout/부분 실패 중 해당 처리
- [ ] 단위·Contract·통합 중 해당 테스트
- [ ] 연동 소비자 확인
- [ ] Mock/실제 경계와 민감정보 점검
- [ ] 개인 TODO 작업 로그 갱신
