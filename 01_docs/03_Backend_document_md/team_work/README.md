# 팀 작업 운영 안내

## 현재 역할

| 구분 | 작업자 | 역할 | 핵심 책임 |
|---|---|---|---|
| A | eom | Backend & Case Platform Engineer | MySQL, Case 상태, General API, Repository, Transaction, Event 저장 |
| B | lee | AI & Multi-Agent Engineer | ML/LLM, Agent, 질문, RAG, AI Contract·평가 |
| C | ham | Realtime & Service Integration Engineer | React 연동, Realtime, Mock Adapter, E2E, Docker·배포 |

```text
Frontend(C) → Public API(A) → General API·MySQL(A)
                              ↓ AI Internal Contract
                         AI API·Agent·RAG(B)

Event Producer(A/B) → 저장·발행(A) → 구독·화면 반영(C)
```

## 코드 소유권

| 영역 | 향후 책임 | 필수 협업 |
|---|---|---|
| `backend/general_api/**`, `migrations/**` | A | B의 AI 입력, C의 UI 요구 Review |
| `contracts/public_api/**` | A 최종 편집 | C 소비자 Review, B 영향 Review |
| `backend/ai_api/**`, `contracts/ai_internal/**` | B | A 소비자 Review |
| `frontend/**` | C | A Public Contract, B AI 표현 Review |
| Event Contract | A/B/C 공동 | A 저장·발행, B producer, C subscriber |
| `docker/**`, 통합 실행환경 | C | A/B 서비스 실행 Review |
| 공통 dependency·공유 DTO | Task별 1명 | 영향 담당자 Review |

## 기존 기여와 향후 책임

기존 Vertical Slice에는 eom의 AI·General API·MySQL·Frontend 작업, lee의 Public Contract·Schema 작업, ham의 Manager Room·통합 작업이 함께 존재한다. 이 기록은 삭제하지 않는다. 새 문서의 `담당`은 앞으로 유지·추가개발할 책임자를 의미한다.

## 충돌 방지 규칙

1. A는 AI Prompt·Agent 내부 구현과 Frontend 화면을 임의 수정하지 않는다.
2. B는 DB를 직접 Query하거나 Migration·Frontend를 임의 수정하지 않는다.
3. C는 DB Schema와 AI Prompt·Agent 내부 로직을 임의 수정하지 않는다.
4. Contract 변경은 요구자 → 제공자 → 소비자 순서로 합의한다.
5. 기존 기능이 동작하면 보존하고 파일 이동·개명·대규모 재작성은 피한다.
6. 테스트하지 않은 항목은 완료 처리하지 않는다.

## 병렬 작업 방식

```text
B: AI 요구·Schema·Fixture 정의
              ↓
A: 저장·Service·Public API 구현
              ↓
C: Adapter·화면·Realtime·E2E 연결
```

- A는 Migration/Repository/Error test를 독립 진행할 수 있다.
- B는 ML 평가, AI Fixture, 실패 처리 test를 독립 진행할 수 있다.
- C는 화면 Data Source 감사, Adapter 분리, E2E scaffold를 독립 진행할 수 있다.

## 공통 완료 기준

- 구현과 Contract가 일치한다.
- 정상·빈 입력·오류·Timeout/재시도 중 해당 흐름을 테스트했다.
- Mock과 실제 구현의 경계가 명확하다.
- Secret·민감정보·로그를 점검했다.
- 연동 소비자가 실제 또는 Fixture로 검증했다.
- 개인 `todo.md`에 변경 파일·테스트·다음 작업을 기록했다.

## Git 협업 기준

| 담당자 | 작업 Branch |
|---|---|
| A=eom | `new_eom` |
| B=lee | `new_lee` |
| C=ham | `new_ham` |

기능별 Branch를 계속 만들지 않는다. 각자 자기 Branch에서 기능 단위로 Commit·Push하고 `main`으로 PR한다. Merge 후 다른 담당자는 최신 `main`을 자기 Branch에 **merge**한다. 팀 숙련도를 고려해 rebase보다 merge를 기본으로 한다. 공용 Contract 변경은 PR 전에 영향 담당자 Review를 받는다.
