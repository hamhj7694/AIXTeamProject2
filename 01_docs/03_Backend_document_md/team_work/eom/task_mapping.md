# eom 작업 매핑 — A Backend & Case Platform Engineer

## 역할

eom은 데이터와 Case 상태를 안정적으로 저장하고 공개 API로 제공한다.

## 향후 소유 영역

```text
02_workspace/backend/general_api/**
02_workspace/backend/contracts/public_api/**
02_workspace/backend/migrations/**
02_workspace/backend/scripts/apply_migrations.py
Backend Error·Validation·Transaction·Event 저장
```

## 핵심 책임

- MySQL Schema, Migration, Transaction, Repository
- Shared Case 구조와 상태전이
- Case/Message/Verification/Action/Event API
- Timeline/Event append·cursor·감사 추적
- Public API DTO·Error·Validation의 Backend 구현
- B의 AI 결과를 검증·저장하고 C에 안정적인 API 제공

## 작업 순서

| Phase | 목표 | 대상 | 완료 조건 |
|---|---|---|---|
| A-0 | 현재 DB/API 기준선 재검증 | migrations, repository, tests | Migration·Create/List/Get·rollback 재현 |
| A-1 | Shared Case/Public Contract | public DTO, Case service | List/Get/Patch DTO와 enum test |
| A-2 | MySQL 안정화 | repository, migration script | 실제 DB transaction·idempotency test |
| A-3 | 상태·Message·Event | Case/Message/Event domain | 상태전이, create/list/cursor test |
| A-4 | Verification·Action | 새 domain·migration | 생성·응답·상태·history test |
| A-5 | Realtime 제공 기반 | Event publisher 경계 | 저장 성공 후 Event 전달 가능 |
| A-6 | Backend 안정화 | errors/config/auth/tests | 공통 오류·권한·관측 test |

## 수정하지 않을 영역

- `backend/ai_api/**`, AI Prompt·Agent·RAG 내부 로직
- `frontend/**` 화면 구현
- lee·ham 개인 작업 문서

B의 새 필드는 B가 의미·Schema·Example을 먼저 정의한다. Frontend 공개 응답 변경은 C의 소비자 Review를 받은 뒤 반영한다.

## 과거 구현 기여

eom이 기존 Vertical Slice에서 구현한 AI API, General API, MySQL Repository·Migration, Frontend 연결 기록은 유지한다. 향후 AI 내부 소유권은 B=lee, Frontend/통합 소유권은 C=ham으로 바뀌었으며 과거 기여를 삭제한다는 의미가 아니다.

## Codex 수칙

1. General API·Migration·Repository와 기존 transaction 방식을 먼저 읽는다.
2. 기존 동작을 보존하고 대규모 파일 이동·재작성을 하지 않는다.
3. DB 변경에는 Migration과 rollback/test를 함께 작성한다.
4. AI 내부 Contract 또는 Frontend 변경이 필요하면 직접 수정하지 말고 영향과 요구를 보고한다.
5. 테스트하지 않은 기능은 완료로 표시하지 않는다.

## 작업 Branch

`new_eom`을 사용한다. 기능별 Branch를 추가 생성하지 않고 최신 `main`을 merge 방식으로 반영한다.
