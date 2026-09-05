# CSR | Case Share Room V4 — CURRENT SOURCE OF TRUTH

**Version:** 1.5  
**Last Updated:** 2026-09-06

## Priority

1. 이 `00_SOURCE_OF_TRUTH.md`
2. 승인된 `01_PRD.md` (CSR V4 v1.2)
3. V4 Architecture / Data Contracts
4. V4 실행 코드
5. V4 Implementation Status
6. V3 코드 — AI Engine/검증된 계약 참고용
7. V3 PRD/PPT 및 과거 TODO/작업로그

## Locked Product Decisions

1. CSR은 탐지 정확도 경쟁이 아니라 탐지 이후의 **Context & Verification Layer**다.
2. 은행과 고객은 서로 다른 화면을 사용하지만 **동일한 Shared Case**를 공유한다.
3. 제품 UX는 **Chat-first Shared Case Workspace**다.
4. 사용자는 Agent를 직접 선택하지 않는다.
5. AI의 기본 경험은 **자연스러운 Conversational Core**다.
6. AI는 요청마다 `DIRECT / RAG / TOOL / AGENT / COMPOSITE` 중 필요한 최소 경로를 선택한다.
7. Case Orchestrator는 **rule/state/policy 우선**이며, 복합 상황에서만 LLM planner가 작업 후보를 제안한다.
8. Customer/Verification/Bank Agent는 같은 Case Snapshot을 사용하되 role/visibility/tool policy를 분리한다.
9. 모든 Agent를 모든 Event/Message에서 호출하지 않는다.
10. AI는 분석·설명·근거·추천을 제공하고, DB side-effect·고객 심화질문 발송·금융조치 완료는 Backend 검증과 Human-in-the-loop 규칙을 따른다.
11. MVP Text Intake는 원문을 분석 과정에서만 일시 사용한다.
12. ML/Feature Extractor 이후 Context Reconstruction은 **Structured Feature Payload만** 사용한다.
13. V4 Case DB에는 통화 원문 전체 또는 복원 가능한 장문 원문을 기본 저장하지 않는다.
14. 실제 서비스 입력은 `Telecom AI Context Feature Event → CSR`을 기본 전제로 한다.
15. 신규 은행 대응 업무의 유일한 원본은 `Task`다.
16. CustomerProgress와 내부 Task는 자동으로 동일 상태가 아니다.
17. Recovery Navigator를 열었다고 실제 지급정지·신고·구제가 완료된 것이 아니다.
18. V4는 Frontend + General Backend + V4 DB를 `MVP_v4`에 새로 구축한다.
19. V3는 동결한다. V3 DB/migration을 V4에 적용하지 않는다.
20. 기존 ML/LLM/RAG/WorkCard/Verification AI Engine은 재사용하고 core logic을 불필요하게 복제하지 않는다.
21. **실시간에 가까워야 하는 것은 Structured Shared Case State이지 자연어 Live Report가 아니다.**
22. 상시 자동 Live Report를 만들지 않는다.
23. AI Case Brief는 최초 Case 생성, 정의된 중요 상태 변화, 또는 은행 직원 명시 요청에서만 갱신한다.
24. Final Report는 Case 종료 시 전체 Case를 기반으로 생성한다.
25. V4 MVP 상태 동기화 기본은 **change-aware revision/fingerprint polling + Entity ID 병합**이다.
26. SSE는 안정적으로 필요할 때 추가할 수 있으나 MVP 필수조건이 아니다. WebSocket은 후순위다.
27. background update는 local draft, focus, cursor, selection, IME를 초기화하지 않는다.
28. polling tick, 패널 open/close, memo/bookmark 변경, 동일 payload는 AI Trigger가 아니다.
29. Fine-tuning은 V4 MVP 선행조건이 아니다. Prompt/Role Policy → Shared Case Context → RAG → Tool routing → Evaluation을 먼저 안정화한다.
30. 변경 가능한 공식지식·연락처·피해구제 절차는 Fine-tuning이 아니라 RAG/검증 DB/Tool이 담당한다.
31. 향후 Fine-tuning 판단을 위해 AI route/tool/result/accept-edit-reject/schema/grounding/cost 로그를 남기되 민감 원문을 자동 학습 데이터로 축적하지 않는다.
32. CUSTOMER / BANK_INTERNAL / AI_PRIVATE visibility를 서버에서 강제한다.
33. expected_version/revision, idempotency, stale AI write 방지, 직원 확정정보 overwrite 방지, 감사 Event를 유지한다.


## Hard Runtime Isolation — NON-NEGOTIABLE

완성된 V4는 **`MVP_v4` 안의 애플리케이션 코드·모델·프롬프트·계약·마이그레이션·정적 자산만으로 실행**되어야 한다.

- V3는 개발 중 AI Engine 확인용 read-only reference일 뿐 runtime dependency가 아니다.
- V3 코드를 재사용하면 반드시 V4 내부로 이식한다.
- V4에서 `MVP_v3`, sibling repo, 외부 로컬 파일을 import/read하는 코드 0건.
- `sys.path`/`PYTHONPATH` hack 0건.
- V3를 향하는 symlink 0건.
- 모델/프롬프트/RAG config도 V4 내부 또는 명시적으로 승인된 외부 network service만 사용.
- 완료 전 `MVP_v4` 단독 복사 환경에서 build/test/health/E2E를 통과한다.
- V3 폴더를 삭제/rename해도 V4가 동작해야 한다.

허용 외부 인프라: Ubuntu/Nginx/MySQL/승인된 외부 AI API/서버에서 V4 안에 생성한 `.venv`.
Nginx serving을 위한 `/var/www/mvp_v4`는 V4의 `frontend/dist`에서 생성·복사된 배포 산출물만 허용한다.

## AWS / Frontend Deployment Lock

- Python 3.11 기준 `/home/ubuntu/MVP_v4/.venv`를 서버에서 새로 생성.
- dependency는 `backend/requirements.txt`.
- `.env`는 서버에서 생성, `.env.example`은 전체 변수 이름 포함.
- production frontend는 `npm ci → npm run typecheck → npm run build`.
- Nginx serving 대상은 `frontend/dist` 산출물.
- Browser는 `/api/*`로 General API만 호출.
- General API `127.0.0.1:8100`, AI API `127.0.0.1:8101`.
- attachment 등 runtime path는 `/home/ubuntu/MVP_v4/backend/data/...` 기본.
- Component에서 `crypto.randomUUID()` 직접 호출 금지.
- 공통 UUID helper: randomUUID 가능 시 사용, 아니면 getRandomValues 기반 RFC4122 v4 fallback.
- localhost/HTTPS/AWS HTTP IP 조건에서 핵심 흐름이 깨지지 않아야 한다.


## Secret Access Lock — NON-NEGOTIABLE

- Codex는 실제 `.env` 및 Secret 가능성이 있는 `.env.*` 파일의 내용을 읽지 않는다.
- `.env.example`만 읽고 수정할 수 있다.
- 환경변수 이름은 코드/Settings schema/`.env.example`에서 파악한다.
- Secret 값이 필요한 경우 `[USER_SECRET_REQUIRED]`로 필요한 변수 이름만 요청한다.
- `.env`의 값을 검색·로그·출력·복사하지 않는다.
- Runtime의 `load_dotenv()` 사용과 개발 Agent의 직접 `.env` 열람을 구분한다.
- 실제 `.env`는 Git에서 제외한다.

## Initial Folder Lock

Repository 구조는 다음을 기준으로 한다.

```text
<repo-root>/
├─ MVP_v3/    # read-only reference
└─ MVP_v4/    # new implementation root
```

V4의 Frontend, General Backend, AI API runtime copy, models, prompts, contracts, migrations, deployment files, docs, tests는 모두 `MVP_v4` 내부에 둔다.

V4 실행코드를 Repository root나 다른 sibling 폴더에 생성하지 않는다.


## Durable Resume Lock — NON-NEGOTIABLE

V4 작업 연속성은 Codex Chat 기억에 의존하지 않는다.

필수:
- `MVP_v4/AGENTS.md`
- `docs/02_IMPLEMENTATION_PLAN.md`
- `docs/03_IMPLEMENTATION_STATUS.md`
- `docs/06_TODO.md`
- `docs/07_WORK_MAPPING.md`
- `docs/08_HANDOFF_CHECKPOINT.md`
- `docs/09_DECISION_LOG.md`

모든 작업은 고유 Task ID를 사용한다.

매 세션 시작:
`AGENTS → SOURCE_OF_TRUTH → IMPLEMENTATION_STATUS → TODO → WORK_MAPPING → HANDOFF → git status/diff`

매 원자 작업:
`IN_PROGRESS 기록 → 구현 → test → Status/TODO/Mapping/Handoff 갱신`

중단 예상 시:
새 큰 작업을 시작하지 말고 현재 작업을 safe checkpoint로 만든 뒤 `08_HANDOFF_CHECKPOINT.md`에 `NEXT_EXACT_STEPS`를 남긴다.

다음 세션은 전체 재감사부터 시작하지 않고 Handoff의 다음 단계부터 현재 코드와 테스트를 검증해 이어간다.

Phase Gate의 local checkpoint commit은 허용하지만 자동 push는 금지한다.

## Historical Document Rule

V3 및 과거 문서는 참고자료다. 과거 문서의 설명만으로 V4 구조를 되돌리거나 legacy 패턴을 복원하지 않는다.

특히 과거의 다음 설계를 V4에 자동 복원하지 않는다.
- SSE를 MVP 기본 전제로 두는 설계
- 모든 Event마다 Live Report Section을 자동 재생성하는 설계
- actions/task 이중 Source
- polling마다 전체 Case object를 교체하는 설계
- Agent를 사용자에게 직접 노출하거나 선택시키는 설계

문서와 V4 코드가 충돌하면 임의로 과거 상태로 복구하지 말고 Conflict를 기록하고 이 Source of Truth 기준으로 정합화한다.
