# CONTEXT-FIRST CASE — AI Engineering Principles

## 1. 문서 목적

이 문서는 CONTEXT-FIRST CASE에서 AI, Agent, RAG, Backend Integration을 확장할 때 따르는 공통 설계 원칙이다. 목표는 DB 스키마, 화면 구조, 외부 API, 모델 또는 프롬프트가 바뀌어도 AI 핵심 판단 흐름을 최소 범위로 유지하는 것이다.

이 문서는 설계 원칙을 정의하는 문서이며, 현재 구현 상태 자체의 Source of Truth는 아니다. 현재 구현 여부와 Contract의 실제 형태는 **실제 Contract → 실제 코드 → 테스트 및 검증 결과 → 설계/설명 문서** 순서로 확인한다. 문서와 구현이 충돌하거나 문서가 오래된 것으로 의심되면 문서 설명만으로 새 코드를 작성하지 않고 실제 Contract·코드·테스트를 먼저 확인한다.

이 구분은 문서의 가치를 낮추기 위한 것이 아니다. 본 문서는 설계 방향, 변경 비용을 줄이는 기준, Codex 작업 원칙, Integration 경계에 대한 Source of Guidance 역할을 하며, 현재 구현 사실은 실제 코드와 테스트로 확인한다.

AI는 최종 금융 조치의 실행자나 사실의 최종 확정자가 아니다. AI 결과는 근거, 불확실성, 경고 및 사람 검토 필요 여부를 함께 전달하는 의사결정 지원 정보다.

## 2. 한 줄 핵심 원칙

**변경 가능성이 높은 값은 한 곳에서 관리하고, DB·Frontend·외부 API의 변화는 Config·Adapter·Mapper 경계에서 흡수하며, AI Domain Core는 안정적인 의미 기반 Contract에만 의존한다.**

## 3. 현재 프로젝트 전제

현재 B 영역에는 ML 위험 진단, LLM 맥락 분석, Structured Case Brief, 질문 후보 생성, 고객 답변 구조화, Brief 갱신, 역할 기반 Agent와 명시적 `AgentRouter`가 있다. `StructuredCaseFacts`와 Context Narrative는 별도 PoC로 존재한다.

AI 내부의 대표 Contract는 `CaseBrief`, `QuestionCandidate`, `CustomerAnswerResult`, `BriefUpdateResult`다. 이 Contract는 담당자가 검토할 의미 기반 결과이며 DB 행, Public API DTO, 특정 화면의 ViewModel과 동일한 모델이 아니다.

현재 `AgentRouter`는 `BUILD_BRIEF`, `RECOMMEND_QUESTIONS` 같은 명시적 작업을 역할 Agent에 연결하는 Task Router다. 자연어 Chat Intent Router는 아직 확정·구현된 것으로 간주하지 않는다. UI도 Page/Panel 중심에서 Chat 중심으로 변경 중이므로, 본 문서는 특정 화면 또는 DB 명칭에 의존하지 않는다.

## 4. Single Source of Truth

같은 의미를 가진 값이 여러 파일에 반복되면 변경 시 누락과 불일치가 생긴다. API URL, API key의 **환경변수 이름**, 모델명, timeout, threshold, prompt/model/feature/contract version, 실행 모드, 공유 상태값은 변경 가능성과 공유 범위를 보고 한 곳에서 정의하거나 한 경로로 참조한다.

현재 구현은 `OPENAI_API_KEY`, `OPENAI_EVENT_MODEL`, `OPENAI_CONTEXT_MODEL`, `OPENAI_CASE_BRIEF_MODEL`, `OPENAI_TIMEOUT_SECONDS`, `DIAGNOSIS_EXTRACTOR_MODE` 등을 환경변수로 읽는다. 모델 bundle/diagnosis fixture에는 `model_version`, `feature_version`도 보존된다. 이는 현재 코드에 전용 중앙 Config 객체가 이미 있다는 뜻은 아니다. 새 Config 구조나 리팩터링은 실제 중복과 변경 비용을 확인한 뒤 별도 작업으로 결정한다.

문제 → 같은 모델명이나 timeout을 서비스마다 직접 작성한다.

원칙 → 공통 환경설정 또는 명시된 설정 경로를 참조한다.
적용 → 값 변경 시 영향 지점을 한 곳 또는 제한된 경계로 줄인다.

## 5. Secret / Environment Configuration

API key, DB password, token, secret key는 코드·프롬프트·fixture·문서에 직접 넣지 않는다. 실제 비밀 값은 `.env` 같은 로컬 환경설정으로 관리하고, `.gitignore`가 `.env`를 제외하는지 확인한다. 이 저장소의 `.gitignore`에는 `.env` 제외 규칙이 있다.

환경마다 달라질 수 있는 API URL, 모델, timeout, DB host, 실행 mode도 가능한 한 환경설정 경계에서 다룬다. 문서·로그·오류 보고에는 키의 존재 여부나 변수명만 기록하고 실제 값을 출력하지 않는다.

## 6. Stable AI Domain Contract

AI Domain Contract는 AI가 사건을 이해하고 안전하게 전달하기 위한 의미 모델이다. 예를 들어 `CaseBrief.impersonation_target`은 특정 DB 컬럼명이나 화면 레이블이 아니라 “사칭 대상”이라는 도메인 의미를 나타낸다.

DB가 `fraud_target`에서 `impersonated_party`로 바뀌더라도, 의미가 유지된다면 DB-to-AI mapper가 이를 AI의 `impersonated_entity` 또는 기존 Contract의 대응 필드로 변환하는 것을 우선한다. DB 명칭을 모든 Agent, Prompt, RAG metadata로 전파하지 않는다.

반대로 `credential_request`와 `credential_exposure`는 각각 상대방의 요구와 고객의 실제 노출이라는 다른 사건이다. 이름만 비슷하다는 이유로 하나의 필드 또는 enum으로 강제 통합하지 않는다. 의미가 변하면 Contract 변경, migration, consumer 검토, 회귀 테스트가 필요하다.

## 7. Adapter / Mapper Boundary

```text
DB / Backend DTO
        ↓
Adapter / Mapper
        ↓
AI Domain Contract
        ↓
AI Service / Agent
        ↓
AI Output Contract
        ↓
Adapter / Mapper
        ↓
Backend / DB / Chat
```

Adapter/Mapper는 단순 이름 변환만 하는 층이 아니다. 타입, 단위, null 정책, version, 출처, 경고 전달 여부를 명시적으로 검증하는 경계다. DB 또는 Public API가 변하면 먼저 이 경계를 수정할 수 있는지 검토한다.

단, 의미가 달라졌거나 하나의 새 값이 여러 기존 사실을 필요로 하면 mapper만으로 해결되지 않는다. 이때는 AI Contract와 소비자 영향 범위를 명시하고 합의한다. mapper가 오류·`warnings`·`partial_failure`·근거를 삭제하여 화면이 정상 결과처럼 보이게 해서는 안 된다.

## 8. Request vs Actual State

상대방이 요청한 행위와 고객이 실제 수행한 행위는 분리한다.

| 요청/시도 사실 | 실제 상태 |
| --- | --- |
| `TRANSFER_REQUEST` | `TRANSFER_COMPLETED` |
| `APP_INSTALLATION_REQUEST` | `APP_INSTALLED` |
| `CREDENTIAL_REQUEST` | `CREDENTIAL_EXPOSURE` |
| `PERSONAL_INFORMATION_REQUEST` | `PERSONAL_INFORMATION_EXPOSURE` |

`StructuredCaseFacts`는 현재 주로 상대방의 사칭·주장·요구·시도를 evidence와 함께 추출한 proposal이다. `CustomerAnswerResult`와 향후 Runtime Case State는 고객이 실제로 무엇을 했는지 확인하는 정보다. DB 또는 UI 편의를 위해 둘을 합치면 위험도, 질문 우선순위, 후속 조치의 의미가 왜곡될 수 있다.

## 9. UI Independence

AI Core는 ROOM Card, Panel 이름, Page 전용 필드처럼 특정 표현 방식에 의존하지 않는다. AI는 `CaseBrief`, 질문 후보, 답변 구조화 결과처럼 의미 기반 출력을 만들고, Frontend가 이를 카드·타임라인 등으로 표현한다. 향후 Chat 중심 구조가 확정되면 별도의 presentation 경계에서 같은 결과를 대화 표현으로 변환할 수 있다.

따라서 Page에서 Chat으로 UI가 바뀌어도 Question Service, Brief Service, Agent의 핵심 로직을 다시 작성하지 않는다. Chat UI와 그 표현 경계의 구체적 형태는 아직 확정하지 않으며, 표시 문구·정렬·interaction 상태는 확정된 presentation 경계에서 다룬다.

## 10. Service / Agent Responsibility

Service는 재사용 가능한 도메인 로직을 소유하고, Agent는 역할 경계와 orchestration을 담당한다. 현재 역할 기반 Agent는 `MvpWorkflowService`를 호출하는 facade이며 같은 business logic을 복사하지 않는 방식이다.

- `CaseSupportAgent`: brief 생성
- `CustomerVerificationAgent`: 질문 추천과 고객 답변 구조화
- `CaseUpdateAgent`: 구조화된 답변을 brief에 반영

공통 규칙을 Agent마다 재구현하면 한 정책 변경이 여러 경로에 퍼진다. 새 Agent가 필요하면 먼저 기존 Service를 호출해 해결되는지 확인하고, 실제 역할별 규칙이 생길 때만 최소한의 로직을 추가한다.

## 11. Router Boundary

명시적 task routing, 향후 Chat intent 해석, 도메인 서비스 실행, Agent business logic은 서로 다른 관심사다.

```text
Chat 입력 → Intent 해석(향후) → 명시적 작업 선택 → Agent → Domain Service
```

Chat Router의 UX·분류 모델·명령 형식이 바뀌어도 `CaseBriefService`나 `QuestionService`의 입력·출력 의미가 바뀌지 않도록 한다. 향후 Chat Router의 구체적 구현은 확정 전까지 가정하지 않는다.

## 12. Prompt / Model / Config Versioning

Prompt 긴 문자열을 여러 service 함수에 중복하지 않는다. 현재 case-support 영역은 `brief_prompt.py`, `question_prompt.py`처럼 prompt 정의를 분리하고 `CASE_BRIEF_PROMPT_VERSION`, `QUESTION_PROMPT_VERSION`을 둔다. 이 기존 방식은 유지·확장 시 참고 대상이다.

Prompt version은 지시문과 출력 형식의 버전이고, model version은 모델 또는 학습 artifact의 버전이며, feature version은 입력 feature 정의의 버전이다. 세 값을 하나의 문자열로 혼합하지 않는다. Prompt·모델·threshold·extractor mode를 바꾸면 적용 버전, fixture/evaluation 결과, known gap을 함께 기록한다.

## 13. Enum / Status / Constant Management

`P0/P1/P2`, `HUMAN_REVIEW_REQUIRED`, `AI_EXTRACTED`, `HUMAN_CONFIRMED`, `VERIFIED`처럼 도메인 의미가 있고 여러 consumer가 공유하는 값은 Contract/Enum으로 관리한다. 현재 AI Internal Contract의 `QuestionPriority`, `TargetField`, `ExecutionMode`가 그 예다.

모든 문자열을 Enum으로 만들지는 않는다. 여러 곳에서 공유되는지, 변경 가능성이 있는지, 오타가 위험한지, 외부 Contract인지에 따라 결정한다. 문장형 안내 문구나 한 곳에서만 쓰이는 고정 설명까지 과도하게 중앙화하지 않는다.

## 14. RAG Knowledge vs Runtime State

RAG Knowledge는 재사용 가능한 문서와 metadata이고, Runtime State는 개별 사건의 현재 상태다. 예를 들어 runtime의 `transaction_status=COMPLETED`와 문서 metadata의 `applicable_transaction_status=[ATTEMPTED, COMPLETED]`는 역할이 다르다.

Knowledge metadata는 `knowledge_purpose`, `consumer_role`처럼 업무 의미를 중심으로 설계하고 특정 Agent 클래스명이나 현재 화면명에 묶지 않는다. embedding model, vector DB, retriever가 바뀌어도 원문과 업무 metadata를 불필요하게 다시 작성하지 않는 구조를 우선한다. 현재 RAG pipeline은 미구현이므로 이를 구현 완료 상태로 표현하지 않는다.

## 15. External API Boundary

OpenAI와 향후 Provider 호출은 AI Domain Logic 전체에 흩어놓지 않는다. 호출 경계에서 인증, 모델 선택, timeout, 응답 형식, 재시도/fallback 정책, 비용 관측, mock 대체를 관리할 수 있어야 한다.

현재 OpenAI 호출이 diagnosis extractor와 brief 보강 경로에 존재하지만, 이는 복잡한 Provider Factory가 이미 필요하다는 뜻은 아니다. Provider 변경 가능성이나 테스트 필요성이 실제로 생길 때 작은 adapter부터 도입한다.

## 16. Failure / Warning Preservation

AI 결과는 성공/실패 이분법이 아니다. `unresolved`, `warnings`, `partial_failure`, evidence 부족, human review 필요 상태를 output Contract에서 보존한다. mapper와 API consumer는 이 정보를 누락·완화·정상화하지 않고 전달 가능한 표현으로 변환한다.

이 원칙은 “AI가 확신하지 못한 사실을 확정처럼 보이지 않게” 하는 안전 장치다. 사용자는 부분 결과를 볼 수 있지만, 어떤 범위가 미확인인지도 함께 알아야 한다.

## 17. Evidence / Provenance

다음 세 층은 구분한다.

```text
Raw Evidence → AI Extracted Fact → Generated Narrative
```

원본 evidence는 관찰 가능한 입력, structured fact는 evidence에 연결된 AI 추출 proposal, narrative는 사람이 읽기 위한 생성 결과다. Narrative를 원본 사실처럼 저장하거나, fact의 provenance를 버리지 않는다. `StructuredCaseFacts`도 현 시점에는 canonical truth가 아니라 evidence-linked AI extraction proposal로 취급한다.

## 18. Regression / Testability

공유 Contract, parser, mapper, prompt, 모델 설정을 바꾸면 기존 workflow가 깨질 수 있다. 변경은 다음 경계에서 fixture 중심 회귀 테스트로 확인한다.

- Contract: JSON schema/model validation과 producer-consumer 정합성
- Service/Agent: brief → question → answer → update 흐름과 human-review guardrail
- Parser/Mapper: 입력 누락, 의미 충돌, version 차이, warning 전달
- External API: timeout, partial failure, mock/fallback

현재 Structured Case Facts·Context Narrative PoC와 AI MVP 관련 테스트가 존재한다. 새 통합 기능은 특정 DB나 Frontend에 과도하게 묶인 테스트보다, 도메인 입력·출력과 adapter 경계를 각각 검증하는 테스트를 우선한다.

## 19. 변경 비용 체크리스트

변경 전 다음을 확인한다.

1. 이 값이 변경되면 몇 파일과 몇 consumer를 수정해야 하는가?
2. DB 컬럼명 변경이 Agent/Prompt/RAG까지 전파되는가?
3. UI 또는 Chat 변경이 AI Contract 의미 변경을 강제하는가?
4. model·threshold·prompt·enum이 여러 파일에 중복되는가?
5. mapper 하나로 흡수할 수 있는 이름/형식 차이인가?
6. 서로 다른 의미를 구현 편의상 하나로 합치고 있지는 않은가?
7. 외부 API 변경이 도메인 규칙까지 침투하는가?
8. failure, warning, evidence, human review가 소비자에게 보존되는가?
9. 기존 회귀 테스트와 fixture가 변경 영향을 검증하는가?
10. 이 추상화가 MVP 기간에 실제 복잡성을 줄이는가?

## 20. 과도한 추상화를 피하는 기준

중앙화 대상은 “변경 가능성이 높고 여러 곳에서 공유되는 것”부터다. 교육 프로젝트/MVP에서 대규모 DI framework, 불필요한 microservice 분리, 모든 문자열 상수화, 복잡한 Agent 상속 구조, 사용처 없는 Provider Factory, 범용 mapper framework는 도입하지 않는다.

문제 → 미래를 모두 대비하려다 현재 구현·테스트 비용이 증가한다.

원칙 → 실제 중복과 변경 요청이 확인된 경계에만 작은 추상화를 둔다.
적용 → 한 서비스와 한 adapter로 충분하면 그 구조를 유지하고, 반복되는 책임이 명확해질 때 확장한다.

## 21. 프로젝트 적용 예시

### Example A — API Key 변경

문제: 여러 서비스에 API key가 하드코딩되어 있으면 교체 시 누락·유출 위험이 있다.

원칙: `OPENAI_API_KEY` 같은 환경변수 이름만 코드가 참조하고 실제 값은 `.env`에 둔다.
적용: key 교체는 배포/개발 환경의 secret 설정에서 수행하며 코드·문서·git에 실제 값을 남기지 않는다.

### Example B — DB 컬럼명 변경

문제: DB의 `fraud_target`이 `impersonated_party`로 변경되면 AI 전체가 DB 명칭을 사용하고 있을 경우 연쇄 수정이 필요하다.

원칙: AI Contract는 `impersonated_entity` 같은 의미를 유지하고 DB-to-AI mapper가 컬럼 차이를 흡수한다.
적용: 의미가 동일하면 mapper와 mapper test만 먼저 바꾼다. 의미가 달라졌다면 Contract 변경과 consumer review를 별도 작업으로 수행한다.

### Example C — Frontend Page → Chat 구조 변경

문제: Panel 이름을 AI output 필드로 사용하면 Chat 전환 때 Service까지 바뀐다.

원칙: AI는 `QuestionCandidate`와 `CaseBrief`를 반환하고 UI가 카드 또는 메시지로 표현한다.
적용: 향후 Chat 중심 구조가 확정되면 Chat presentation adapter 등의 경계에서 질문 결과를 대화 표현으로 변환할 수 있으며, Question Service의 우선순위·근거 규칙은 유지한다.

### Example D — AI Model 변경

문제: 모델명이 extractor와 brief service에 개별 하드코딩되면 변경 범위를 파악하기 어렵다.

원칙: 현재 사용하는 환경변수 경로를 통해 모델을 선택하고, model version과 prompt version을 구분한다.
적용: 모델 변경 시 timeout·비용·출력 정합성·fixture/evaluation 결과를 함께 점검한다. 전용 중앙 Config 도입은 실제 중복 확인 후 결정한다.

### Example E — Request vs Actual State

문제: “송금을 요구받음”을 “송금 완료”로 저장하면 사실과 위험 상태가 섞인다.

원칙: 요청/시도는 Structured Fact, 고객의 실제 수행은 `CustomerAnswerResult` 또는 Runtime State로 분리한다.
적용: 고객이 “아직 송금하지 않았다”고 답하면 transfer request evidence는 보존하고 completed 상태를 만들지 않는다.

## 22. Codex 작업 시 체크리스트

### 작업 전

- [ ] 프로젝트 `AGENTS.md`, 담당 `task_mapping.md`, `todo.md`, 작업 카탈로그를 확인했다.
- [ ] 실제 Contract, 구현, 테스트, 기존 설정을 읽기 전용으로 확인했다.
- [ ] 새 값이 기존 설정/Enum/Prompt/Contract와 중복되지 않는지 확인했다.
- [ ] DB, Public API, Frontend 등 담당 외 영역 영향은 담당자와 합의할 범위로 분리했다.

### 작업 후

- [ ] 변경 가능한 값을 새로 하드코딩하지 않았다.
- [ ] 기존 business logic을 Agent 또는 Service에 중복 복사하지 않았다.
- [ ] DB/UI/외부 Provider 변화가 AI Core에 직접 결합되지 않았다.
- [ ] warning, unresolved, partial failure, evidence, human review가 보존된다.
- [ ] 관련 regression test 또는 fixture 검증 결과를 기록했다.
- [ ] prompt/model/feature/contract 변경이면 버전과 evaluation 결과를 기록했다.
- [ ] 담당 `todo.md`와 전체 task catalog의 상태를 실제 구현·테스트 결과에 맞게 갱신할 필요가 있는지 확인했다.

## 23. 향후 통합 점검 체크리스트

아래 항목은 현재 구현 완료로 간주하지 않으며, 통합 시 별도 Contract·담당자 합의·테스트가 필요하다.

- DB ↔ AI mapper와 versioned case input
- 향후 Chat ↔ AI Contract/presentation 경계
- RAG ↔ Structured Facts mapping 및 knowledge freshness 정책
- Runtime Case State와 verification status transition
- A=eom Backend의 case/message/event 조회·저장 Contract와 AI workflow 연결
- A/C consumer를 위한 `warnings`·`partial_failure`·human-review 표현 정책
- 운영 LLM provider/model, embedding model, vector DB, 비용·timeout·fallback 정책
