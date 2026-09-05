# CSR | Case Share Room V4 Rebuild PRD

**제품:** CSR | Case Share Room  
**문서 버전:** V4 Rebuild Baseline 1.5 — Conversational Agent Engine / Change-aware Shared Case  
**기준일:** 2026-09-06  
**개발 방향:** Frontend + General Backend Clean Rebuild / Existing AI Engine Reuse & Conversational Agent Upgrade  
**제품 유형:** 보이스피싱 양방향 상담·대응 AI 플랫폼 / Context & Verification Layer

> V4는 V3를 계속 패치하는 프로젝트가 아니다. V3에서 검증한 제품 개념·AI 엔진·업무 규칙은 재사용하되, Frontend와 General Backend, V4 데이터 모델과 실시간 상태 갱신 구조는 새로 설계·구축한다.

---

## 1. Executive Summary

CSR | Case Share Room은 **탐지 정확도를 다시 겨루는 서비스가 아니라, 탐지 이후의 사건 파악·진위 확인·고객 설득·피해 차단을 하나의 Case로 연결하는 플랫폼**이다.

범죄자는 기관의 권위, 공포·긴급성, 고립을 이용해 피해자의 독립적인 판단을 어렵게 만든다. 위험신호가 통신사 AI, ASAP, 은행 FDS에서 포착되더라도 탐지 이후에는 은행 직원이 짧은 시간 안에 사건을 다시 파악하고, 고객에게 필요한 사실을 확인하고, 사기를 부인하거나 범죄자의 지시를 신뢰하는 고객을 설득해야 한다.

CSR은 이 구간을 지원한다.

- 통화에서 추출된 맥락 피처
- 고객의 실시간 답변
- 은행 거래/FDS 맥락
- ASAP 위험신호
- 기관·공식절차 검증 결과
- 은행의 업무·조치 결과

를 하나의 **Shared Case**에 축적한다.

Customer Agent, Bank Agent, Verification Agent는 각자의 역할을 수행하고, **Case Orchestrator가 Case Event와 현재 상태를 기준으로 필요한 최소 AI 역할과 Function을 선택하고, 독립적인 작업만 필요할 때 병렬 호출한 뒤 검증된 결과를 같은 Case State에 반영한다.**

사용자는 여러 Agent를 직접 선택하지 않는다. 은행 직원과 고객은 각자 다른 화면을 사용하지만 같은 Case를 공유하며, 대부분의 업무와 상담은 Chat-first 방식으로 진행된다.

---

## 2. Product Problem

### 2.1 기존 체계가 잘하는 것

- 통신사·스마트폰 AI: 통화 위험 탐지와 경고
- ASAP: 기관 간 위험정보 공유
- 은행 FDS: 이상거래·계좌 위험 탐지와 금융조치
- 112·피해구제: 신고, 지급정지, 피해구제

### 2.2 탐지 이후 남아 있는 업무

기존 체계가 위험을 탐지해도 실제 피해를 막기 위해서는 다음 업무가 이어진다.

1. 사건 맥락 재구성
2. 고객 접촉
3. 고객 답변을 통한 사실 확인
4. 범죄자의 사칭 주장·절차 진위 확인
5. 추가 확인 질문 설계
6. 고객에게 상황을 이해시키고 설득
7. 은행 조치 선택·실행
8. 피해 발생 시 신고·지급정지·피해구제 연결

### 2.3 핵심 문제 정의

> 범죄자는 피해자의 판단을 흔들고, 탐지 이후에는 은행 직원이 그 사건을 다시 파악·확인·설득해야 한다. 정말 필요한 것은 더 강한 경고가 아니라, 사건의 상황과 맥락을 빠르게 파악하고 사실 확인·고객 설득·피해 차단을 지원하는 구조다.

---

## 3. Product Positioning

CSR은 기존 탐지·공유·금융조치 시스템을 대체하지 않는다.

| 체계 | 핵심 질문 | 주요 역할 | CSR과의 관계 |
|---|---|---|---|
| 통신사·스마트폰 AI | 이 통화가 위험한가? | 실시간 통화 분석·고객 경고 | Call Risk Trigger |
| ASAP | 기관 간 공유할 위험정보가 있는가? | 표준 위험정보 공유·활용 | Risk Signal |
| 은행 FDS | 이 거래가 이상한가? | 거래·계좌 위험탐지·금융조치 | Financial Protect |
| 112·피해구제 | 피해 후 무엇을 조치할 것인가? | 신고·지급정지·피해구제 | Recovery Channel |
| CSR | 범죄자가 무엇을 주장·요구했고, 무엇을 누구에게 확인해야 하는가? | 발화맥락 구조화·진위검증·상담·설득·업무지원 | Context & Verification Layer |

**핵심 차별성:** 통화 발화 맥락 + ASAP/FDS 신호 + 고객 응답 + 기관 확인 결과를 같은 Case에서 연결한다.

---

## 4. V4 Rebuild Decision

### 4.1 V4를 만드는 이유

V3는 많은 기능을 검증했지만 점진적 추가 과정에서 다음 구조적 부채가 생겼다.

- 같은 사건 상태가 Conversation, Context, Task, Progress, Timeline, Report에 서로 다른 규칙으로 표현됨
- 과거 Action과 신형 Task 등 동일 업무의 원본이 분리된 시점이 있었음
- 카드와 상태 표현 규칙이 일관되지 않아 화면 스캔 비용이 커짐
- polling이 server state 전체를 교체하며 local draft/focus에 영향을 줄 수 있음
- 과거 문서와 최신 코드가 충돌하는 문제가 누적됨
- 기능을 수정할수록 legacy 호환 로직이 새 구조를 오염시킬 위험이 커짐

### 4.2 V4의 범위

**새로 구축**
- Bank Frontend
- Customer Frontend
- General Backend
- V4 DB Schema/Migrations
- Shared Case/Event 모델
- Change-aware 상태 동기화 계층
- V4용 AI Adapter/Orchestration

**최대한 재사용**
- 기존 ML 모델/Bundle/Threshold
- 통화 분석 및 Context Feature 추출 AI
- Question Planner
- Verification RAG
- BANK_ACTION WorkCard 생성
- Customer/Bank용 LLM 프롬프트와 검증된 출력 정책
- Report/Brief 생성 로직 중 재사용 가능한 부분

### 4.3 V3 보존 원칙

- V3 코드는 삭제하지 않는다.
- V3 DB를 V4 개발 중 자동 migration하지 않는다.
- V4는 별도 폴더, 별도 실행 포트, 별도 DB를 사용한다.
- V3 문서는 V4의 구현 기준이 아니다.
- V3에서 기능을 재사용할 때는 개념/계약을 참고하고, 복잡한 Component/Repository를 통째로 복사하지 않는다.

---

## 5. Product Goals

### G1. 탐지된 위험을 사람이 이해할 수 있는 Case로 전환

단순 Risk Score가 아니라 **누가, 무엇을 주장하고, 무엇을 요구하며, 어떤 압박을 사용했고, 무엇이 확인되어야 하는지**를 구조화한다.

### G2. 은행 직원 업무를 빠르게 지원

- 5초: 무슨 사건인지
- 10초: 무엇이 위험하고 무엇이 확인됐는지
- 30초: 다음 질문·검증·조치 실행

### G3. 고객을 혼자 판단하게 두지 않음

고객은 복잡한 위험정보를 직접 해석하지 않고, AI와 대화하며 상황을 확인하고 안전행동을 수행한다.

### G4. 고객과 은행을 같은 Shared Case로 연결

고객이 답한 내용이 채팅에서 끝나지 않고 구조화된 Case 정보가 되어 은행 대응에 반영된다.

### G5. 예방부터 Recovery까지 동일 사건을 재사용

예방 단계에서 확보한 Case 정보를 지급정지·신고·피해구제 과정에 다시 활용한다.

### G6. AI와 사람의 책임 경계 유지

AI는 분석·구조화·설명·근거·추천을 제공하고, 최종 금융판단과 실행은 사람 또는 기존 금융 시스템이 수행한다.

---

## 6. Non Goals

V4 MVP에서 하지 않는다.

- 실제 통신사 통화 원문 실시간 수집
- 실제 FDS/ASAP Production API 연결
- AI가 자동으로 지급정지·거래차단 실행
- AI가 승인 없이 고객에게 심화질문 또는 금융조치 문구 발송
- AI가 112 신고·피해구제를 실제 접수 완료 처리
- V3 전체 DB 자동 마이그레이션
- 운영 수준의 IAM/RBAC 완성
- 통신사/은행/경찰 시스템 전체 대체

---

## 7. Primary Users

### 7.1 은행 담당자

필요:
- 사건을 빠르게 이해
- 고객과 소통
- 확인 질문 생성·전달
- 기관·절차 검증
- 대응 업무 기록·실행
- AI 추천 활용
- 사건 상태·근거·Timeline 확인
- 개인 메모·북마크
- 피해 발생 시 Recovery 지원

### 7.2 고객

필요:
- 무엇을 멈춰야 하는지 이해
- 현재 상황 설명
- 필수 안전질문 답변
- 진위 확인 결과 이해
- 은행 담당자와 같은 사건에서 연결됨을 확인
- 피해 발생 시 순서대로 Recovery 안내받기

---

## 8. Core UX Concept — Chat-first Shared Case Workspace

CSR은 카드형 대시보드보다 **Chat-first 업무공간**에 가깝다.

### 은행
- 중앙 Conversation: 대화와 실제 업무 수행
- 우측 Context: 대화를 다시 읽지 않고 사건의 현재 상태를 빠르게 파악하는 압축 영역
- 좌측 Case List: 현재 대응할 사건 선택

### 고객
- Conversation: 설명, 질문, 답변, 검증 결과, 안전행동, Recovery 안내
- Progress: 내부 업무상태가 아니라 `지금 상태 / 완료된 것 / 내가 지금 해야 할 것`

### Chat-first에서 가능한 상호작용

- 일반 상담
- AI에게 사건 질문
- 고객에게 질문 보내기
- 기관 확인 요청
- 대응 업무 기록
- AI에게 대응 업무 추천 받기
- 고객 확인 요청
- 지원 요청
- 결과 확인
- 첨부파일 제출
- 북마크

구조화가 필요한 결과는 Message에만 묻어두지 않고 Question, Fact, Verification, Task, Event 등 별도 Entity로 저장한다.

---

## 9. V4 MVP Test Input → Case Creation Pipeline

### 9.1 왜 Test Input 화면이 필요한가

실제 서비스에서는 통신사 AI가 통화를 분석해 필요한 Context Feature만 CSR에 전달하는 구조가 목표다. 그러나 공모전 MVP에서는 통신사 연동이 없으므로 **테스트용 원문 텍스트 입력 화면**을 둔다.

이 화면은 실서비스 UX가 아니라 **실제 입력 구조를 시뮬레이션하기 위한 개발·시연 장치**다.

### 9.2 MVP 처리 순서

```text
[테스트용 통화 텍스트]
        ↓
문장/구간 분리
        ↓
ML 위험 분석
        ↓
Threshold 미만 → Case 생성하지 않음 / 결과만 표시
Threshold 이상 → Context Feature Extraction
        ↓
원문 폐기 경계
        ↓
Structured Context Features
        ↓
Context Reconstruction LLM
        ↓
Shared Case 생성
        ↓
Case Orchestrator 초기 Agent 호출
```

### 9.3 중요한 데이터 경계

MVP에서도 실제 구조를 흉내 내기 위해 **Context Reconstruction 단계에는 원문 전체를 다시 넘기지 않는다.**

1. Raw text는 분석 요청 동안만 사용
2. ML 분석과 Feature Extractor가 구조화 정보 생성
3. Case 생성 LLM은 구조화된 Feature Payload만 사용
4. V4 DB에는 원문 전체 또는 원문 복원이 가능한 긴 문장 조각을 기본 저장하지 않음

### 9.4 Context Feature 예시

```json
{
  "risk": {
    "score": 0.91,
    "model_version": "window-v2"
  },
  "impersonation": [
    {"entity_type": "PROSECUTION", "label": "검찰"}
  ],
  "claims": [
    {"type": "ACCOUNT_INVOLVED_IN_CRIME", "confidence": 0.92}
  ],
  "demands": [
    {"type": "TRANSFER", "amount_krw": 12000000},
    {"type": "REMOTE_CONTROL_APP_INSTALL"}
  ],
  "pressure_cues": ["AUTHORITY", "URGENCY", "FEAR", "ISOLATION"],
  "exposure_cues": ["PERSONAL_INFORMATION_REQUEST"],
  "entities": {
    "amounts": [12000000],
    "institution_names": ["검찰"]
  },
  "sequence": [
    "IMPERSONATION",
    "CRIME_CLAIM",
    "URGENCY",
    "TRANSFER_DEMAND"
  ]
}
```

### 9.5 실제 서비스 전환

실서비스에서는 위 Feature Payload의 생산자가 CSR 내부 Text Analyzer가 아니라 **통신사 AI/온디바이스 탐지기**가 된다.

```text
Telecom AI Context Feature Event
+ FDS Transaction Event
+ ASAP Risk Signal
+ Customer Emergency Event
→ Case Orchestrator
→ 같은 Shared Case로 병합
```

따라서 V4의 Case Creation API는 Raw Text 전용 계약에 종속되지 않고 **Feature Event를 직접 받을 수 있는 계약**을 별도로 가져야 한다.

---

## 10. Core Architecture

```text
Bank Frontend ─┐
               ├── General Backend / Case Orchestrator ── Conversational AI Engine
Customer Frontend ─┘          │                         ├─ Conversational Core LLM
                              │                         ├─ RAG Retriever
                              │                         ├─ Function / Tool Registry
                              │                         ├─ Customer Role Policy
                              │                         ├─ Bank Role Policy
                              │                         ├─ Verification Agent / RAG
                              │                         └─ Brief / Final Report Generator
                              │
                              ├── MySQL V4 / Shared Case
                              ├── Change-aware Event / Delta Delivery
                              └── Vector DB / Official Data / Function Adapters
```

### 핵심 원칙

- Frontend는 General Backend만 호출한다.
- AI Engine은 **일상적인 자유 대화를 이해하고 응답할 수 있는 Conversational Core**를 기본으로 한다.
- 대화 요청마다 LLM이 무조건 RAG·Function·다른 Agent를 호출하지 않는다. 먼저 `직접 답변 / RAG / Function / Agent handoff` 중 필요한 경로를 선택한다.
- General Backend가 Case State, 권한, 저장, Event, Orchestration, Tool 허용 범위를 책임진다.
- 모든 Agent는 동일한 Shared Case Snapshot을 근거로 하되 CUSTOMER / BANK_INTERNAL / AI_PRIVATE visibility를 지킨다.
- Agent 출력은 자연어 응답과 구조화된 Proposal/Tool Call을 함께 지원한다.
- AI는 DB를 직접 수정하지 않는다. 저장·발송·업무 생성·상태 변경은 General Backend가 검증 후 수행한다.
- 구조화 Case State는 데이터 변경 시 갱신하지만, 자연어 Brief/Report를 모든 Event마다 재생성하지 않는다.

---

## 11. Case Orchestrator

Case Orchestrator는 V4의 중심 Backend Application Service다. **LLM 하나가 모든 것을 자유롭게 판단하는 Agent가 아니라, 규칙·상태머신·Tool 정책과 필요 시 LLM planning을 결합한 중앙 조정 계층**이다.

### 책임

1. Event 또는 사용자 요청 수신
2. 입력·권한·visibility 검증
3. Case 생성 또는 기존 Case 병합
4. 최신 Shared Case Snapshot 구성
5. 요청 유형 판별: 일반 대화 / RAG / Function / Agent / 복합 작업
6. 규칙으로 확정 가능한 Routing 우선 처리
7. 복합적일 때만 LLM Planner가 필요한 작업 후보를 제안
8. 필요한 Agent·Tool 선택 및 독립 가능한 작업 병렬 호출
9. 결과 검증·정규화·출처 연결
10. Human approval가 필요한 결과와 자동 반영 가능한 결과 분리
11. DB 저장 및 CaseEvent 발행
12. 변경된 Entity만 Frontend에 전달

### Orchestration 원칙

- 모든 메시지와 모든 Event에서 모든 Agent를 호출하지 않는다.
- `event_type + user_intent + case_state + unresolved_fields + mode + permissions`를 기준으로 최소 호출한다.
- 단순 인사·설명·이미 Case에 있는 사실 확인은 Tool/RAG 없이 Conversational Core가 답할 수 있다.
- 최신 공식 절차·기관 근거가 필요한 질문은 RAG를 사용한다.
- 데이터 조회·업무 생성·검증 요청처럼 시스템 동작이 필요한 경우에만 Function/Tool을 사용한다.
- 다른 전문 역할이 필요한 경우에만 Agent handoff를 수행한다.
- 동일 입력 지문으로 같은 AI 작업을 반복 호출하지 않는다.
- 오래된 revision에서 생성된 AI 결과는 저장하지 않는다.
- AI 호출은 polling tick, 화면 열기/닫기, 북마크, 메모 변경만으로 발생하지 않는다.

---

## 12. AI Roles

### 12.1 Customer Agent

역할:
- 고객용 사건 브리핑
- 안전한 행동 안내
- P0 안전질문 생성/전달 정책 지원
- 고객 자유응답 구조화
- 피해 발생 여부·노출정보 후보 추출
- 고객에게 쉬운 설명
- 재판단·설득 지원
- Recovery 안내 개인화

### 12.2 Verification Agent

역할:
- 사칭기관 확인
- 범죄자가 주장한 공식 절차 검증
- 공식 연락처·문서·절차와 대조
- Claim별 Verification Evidence 생성
- 상태 판정: 확인 중 / 확인 완료 / 불일치 / 확인 불가

정확한 전화번호·URL 등은 LLM이 임의 생성하지 않고 `official_contacts` 또는 검증된 RAG/DB에서 조회한다.

### 12.3 Bank Agent

역할:
- 통화/Context Feature 해석
- FDS/Transaction Context 해석
- Case Brief
- 추가 확인항목 추천
- 고객 질문 후보
- 대응 업무 후보
- 고객 설득 근거
- 금융조치 검토 지원

### 12.4 Conversational Core

Customer/Bank 화면의 기본 LLM 경험은 챗봇이다. 사용자는 정해진 버튼만 누르는 것이 아니라 자연어로 질문·설명·요청할 수 있어야 한다.

역할:
- 일상적 대화와 사건 관련 질문 이해
- 현재 Case 맥락을 반영한 자연스러운 답변
- 사용자 의도 분류
- RAG가 필요한지 판단
- Function/Tool 실행이 필요한지 판단
- 다른 Agent handoff가 필요한지 판단
- Tool 결과를 사람이 이해할 수 있는 응답으로 합성
- 미확인 정보를 단정하지 않고 필요한 확인을 제안

Customer와 Bank는 같은 Core Model을 재사용할 수 있지만, **System Policy·허용 Tool·visibility·응답 톤·승인 규칙은 역할별로 분리**한다.

### 12.5 Brief / Final Report AI

역할:
- 최초 Case 생성 시 AI Case Brief 생성
- 중요 상태 변경 또는 직원의 명시적 요청 시 Case Brief 갱신
- Case 종료 시 Final Report 생성

**모든 Event마다 자연어 Live Report를 자동 재생성하지 않는다.**

---

## 13. Conversational AI · RAG · Function / Tool Policy

AI는 기본적으로 **대화형 Assistant**로 동작한다. 사용자의 자연어 요청을 이해한 뒤 가장 비용이 낮고 안전한 경로를 선택한다.

### 13.1 Request Handling Loop

```text
User Message / Case Event
→ Intent & Safety Check
→ Case Context 조회
→ Direct Answer 가능?
   ├─ Yes → 자연어 응답
   └─ No
      → RAG 필요?
      → Function/Tool 필요?
      → 전문 Agent 필요?
→ 필요한 최소 작업 실행
→ 결과와 근거 검증
→ Role/Visibility에 맞게 응답
→ 필요한 경우만 구조화 Proposal 반환
```

### 13.2 RAG 원칙

RAG는 모든 메시지에 강제하지 않는다. 다음 상황에서 사용한다.

- 사칭기관·공식절차 확인
- 금융기관/공공기관 공식 안내 확인
- 피해구제 절차·준비자료·주의사항
- 현재 Case의 질문과 관련된 공식 근거 검색

RAG 결과에는 가능한 경우 `source_id / title / effective_date / retrieved_at`을 유지한다. 공식 전화번호·URL·계좌 등 정확값은 LLM이 생성하지 않고 검증된 DB/Tool에서 조회한다.

### 13.3 Function / Tool Registry

AI가 직접 DB를 변경하지 않는다. Agent가 호출하거나 제안할 수 있는 논리 Function 예:

- `get_case_state`
- `search_official_procedure`
- `lookup_official_contact`
- `propose_customer_question`
- `propose_bank_task`
- `request_verification`
- `propose_customer_notice`
- `propose_context_item`
- `propose_fact_candidate`
- `refresh_case_brief`
- `recommend_recovery_step`

Tool마다 다음 계약이 필요하다.
- allowed_roles
- input_schema
- output_schema
- side_effect 여부
- human_approval_required
- idempotency_key 필요 여부
- timeout/retry
- audit event

### 13.4 Agent Handoff

- Customer Agent: 고객 설명·안전질문·안전행동·설득·Recovery
- Bank Agent: 사건 파악·질문 후보·대응 업무 후보·상담 근거
- Verification Agent: 공식근거 검색·Claim 검증

Conversational Core가 다른 Agent의 전문 판단이 필요하다고 판단해도, Orchestrator의 허용 정책을 통과해야 실제 호출한다.

### 13.5 자동 반영 가능한 것

- AI_PRIVATE 분석 결과
- 저위험 구조화 후보
- P0 표준 안전질문 Queue 등록(중복·정책 검사 통과 시)
- 최초/요청 기반 내부 Brief 초안

### 13.6 직원 승인 필요한 것

- P1/P2 사건별 심화질문 고객 발송
- 대응 Task 생성
- 고객에게 공개할 심화 설명
- Verification 결과의 고객 공개
- 금융조치 완료 기록
- Case 종료

### 13.7 Fine-tuning 전략

V4 MVP의 선행조건으로 모델 Fine-tuning을 강제하지 않는다. 우선순위는 다음과 같다.

1. System/Role Prompt 정리
2. Shared Case Context 구성
3. RAG 품질 개선
4. Function/Tool Schema와 Routing 개선
5. 평가 데이터셋과 실패 로그 축적
6. 그 후 Fine-tuning 필요 여부 판단

Fine-tuning 후보 영역:
- 고객/은행 역할별 일관된 말투와 응답 형식
- intent/tool routing 안정성
- 구조화 출력 schema 준수
- 보이스피싱 도메인 표현·질문 생성 패턴
- 불필요한 Tool 호출 감소

최신 공식 지식과 피해구제 절차를 모델 가중치에 넣는 용도로 Fine-tuning하지 않는다. **변경 가능한 지식은 RAG/DB가 담당**한다.

### 13.8 AI Evaluation

AI 품질은 단순 대화 만족도뿐 아니라 다음으로 평가한다.
- Direct / RAG / Tool / Agent route 정확도
- Tool 선택 정확도
- 불필요 Tool 호출률
- RAG 근거 적합도·출처 일치율
- 질문 중복률
- 허위 기관/연락처 생성 0건
- 구조화 출력 schema 성공률
- Bank Task 추천 채택/수정/거절률
- Customer 안전행동 응답의 명확성
- visibility leakage 0건

---

## 14. Shared Case — Single Source of Truth

은행 화면과 고객 화면은 서로 다른 Case를 만들지 않는다.

**하나의 Case + 역할별 Projection** 구조다.

### 주요 Entity

| Entity | 목적 |
|---|---|
| Case | 사건 ID, 상태, 모드, 담당자, 피해 상태 |
| CaseParticipant | 고객/직원 참여자 |
| ContextFeature | 통신/ML에서 들어오는 구조화 맥락 피처 |
| ContextItem | 사칭·Claim·Demand·노출·요약 등 사람이 읽는 구조화 항목 |
| Message | 고객·은행·AI 대화 |
| Question | 구조화 질문 |
| Answer | 질문에 대한 고객 답변 |
| Fact | 제안/확정 사실 |
| Verification | 기관·공식절차 검증 |
| Task | 은행 대응 업무 |
| CustomerProgress | 고객에게 공개되는 진행 상태 |
| AISuggestion | AI 원안과 직원 채택 이력 |
| Event | 모든 주요 상태 변화의 감사 로그 |
| CaseBrief | 현재 사건의 제한적 AI 요약과 갱신 이력 |
| Report | Final Report |
| AIRun | route·model·prompt version·tool/agent 호출·결과·비용·평가 로그 |
| PersonalNote | 직원 개인 메모 |
| Bookmark | 원본 Message/객체 바로가기 |
| Attachment | 증빙 파일 |
| OfficialContact | 공식 전화번호/URL/기관정보 |

---

## 15. Suggested V4 Database Schema

V4는 별도 DB에서 migration `001`부터 시작한다.

핵심 테이블:

- `cases`
- `case_participants`
- `context_features`
- `context_items`
- `messages`
- `questions`
- `question_answers`
- `facts`
- `verifications`
- `verification_evidence`
- `tasks`
- `customer_progress`
- `ai_suggestions`
- `case_events`
- `case_briefs`
- `reports`
- `ai_runs`
- `personal_notes`
- `bookmarks`
- `attachments`
- `official_contacts`

### AI 실행 로그 원칙

`ai_runs`는 운영 로직의 Source of Truth가 아니라 관찰·평가·향후 Fine-tuning 데이터 준비를 위한 로그다.

최소 기록 후보:
- `run_id`, `case_id`, `actor_role`
- `intent`
- `route`: DIRECT / RAG / TOOL / AGENT / COMPOSITE
- `agent_name`, `tool_names`
- `model`, `prompt_version`
- `source_revision` / `case_fingerprint`
- `schema_valid`
- `grounding_sources`
- `latency_ms`
- `input_tokens`, `output_tokens`, `estimated_cost`
- `human_action`: ACCEPTED / EDITED / REJECTED / NONE
- `error_type`

민감한 원문을 Fine-tuning 로그 명목으로 무제한 저장하지 않는다. 학습/평가 데이터는 별도 비식별·승인 절차를 거친다.

### 공통 필드 원칙

변경 가능한 업무 Entity에는 가능한 한 다음을 둔다.

- `id`
- `case_id`
- `version`
- `created_at`
- `updated_at`
- `created_by`
- `updated_by`
- `deleted_at` 또는 명시적 상태

---

## 16. Visibility & Role Projection

기본 visibility:

- `CUSTOMER`
- `BANK_INTERNAL`
- `AI_PRIVATE`

### Customer Projection에 포함 가능

- 고객 공개 Message
- 고객 본인의 질문·답변
- 공개 승인된 Verification Summary
- 고객 Progress
- 안전행동 및 Recovery 안내
- 고객 첨부파일

### Customer Projection에 포함 금지

- BANK_INTERNAL Message
- AI_PRIVATE 분석
- 내부 Risk 계산 상세
- 직원 개인 메모
- 미승인 Verification Evidence
- 내부 Prompt/Agent log
- 다른 고객 정보

---

## 17. Event Model & Change-aware Update

`CaseEvent`는 사건의 변경 이력과 화면 동기화의 기준이지만, **모든 Event가 AI 실행을 의미하지 않는다.**

예:

- CASE_CREATED
- CONTEXT_UPDATED
- MESSAGE_CREATED
- QUESTION_CREATED
- QUESTION_ANSWERED
- FACT_PROPOSED
- FACT_CONFIRMED
- VERIFICATION_REQUESTED
- VERIFICATION_COMPLETED
- TASK_CREATED
- TASK_UPDATED
- TASK_COMPLETED
- TASK_CANCELLED
- CUSTOMER_PROGRESS_UPDATED
- CASE_BRIEF_REFRESHED
- CASE_MODE_CHANGED
- CASE_CLOSED

### MVP Frontend 동기화

V4 MVP의 우선순위는 안정성이다.

- 쓰기: HTTP API
- 현재 사용자가 수행한 Write: 성공 즉시 로컬 Entity 반영
- 다른 사용자/백그라운드 변경: **change-aware revision polling을 기본 허용**
- 동일 revision/동일 fingerprint면 setState 하지 않음
- 변경된 Entity만 ID 기반 병합
- SSE는 안정적으로 구현할 수 있을 때 선택적으로 추가하며 MVP 필수조건이 아니다.
- WebSocket은 더 후순위다.

### AI Trigger와 UI Update를 분리

다음은 화면에는 반영될 수 있지만 AI를 호출하지 않는다.
- 메모 수정
- 북마크
- 패널 열기/닫기
- Task 단순 상태 변경
- 동일 데이터 polling
- Presence

AI는 명확한 사용자 요청 또는 의미 있는 Case 변경에서만 실행한다.

### 중요한 UX 원칙

- 새 데이터가 와도 사용자가 입력 중인 draft/focus/selection/IME 상태를 교체하지 않는다.
- React rerender 자체를 막는 것이 목적이 아니라 불필요한 전체 object replacement와 remount를 피한다.
- 현재 읽고 있는 텍스트가 이유 없이 계속 다시 생성되거나 흔들리지 않아야 한다.

---

## 18. Bank Frontend

### 18.1 Layout

```text
┌──────────────────────────────────────────────────────────────┐
│ Header · Case Title · Status · Assignee                      │
├──────────────┬────────────────────────────┬──────────────────┤
│ Case List    │ Shared Conversation        │ Case Context     │
│              │                            │                  │
│              │                            │ Personal tools   │
└──────────────┴────────────────────────────┴──────────────────┘
```

### 18.2 Left — Case List

최소 표시:
- Case ID
- 사건명/유형
- 사용자 상태: 의심 / 피해 발생 / 해결
- 담당자
- 현재 업무 단계
- 최근 업데이트

### 18.3 Center — Shared Conversation

표현 규칙:
- 고객/직원/AI 일반 대화 → 말풍선
- System Event → 얇은 한 줄
- Question/Verification/Task/Report → 공통 구조형 Shell

공통 Shell:

```text
[아이콘] 제목                         상태
핵심 내용
[필요한 경우에만 Action]
```

### 18.4 Composer Target

오발송 방지를 위해 작성 대상이 명확해야 한다.

- 은행 내부
- 고객에게
- AI에게

기본값은 `은행 내부`를 권장한다.

### 18.5 Quick Actions

- 고객에게 질문
- 기관 확인
- 대응 업무 기록
- AI에게 업무 추천 받기
- 고객 진행 결과 기록
- 보고서/파일

### 18.6 Right — Case Context

기본 영역:
1. 사건 요약
2. 피해·노출
3. 상대방 주장
4. 상대방 요구
5. 확인된 사실
6. 확인 필요
7. 진행 중 할 일

접힌 영역:
- 완료 업무
- 취소 업무
- 고객 공유 결과
- 사건 관리

원칙:
- 카드 남발 금지
- 1줄 정보 중심
- Summary 최대 3~4줄
- 출처/확정상태는 작은 Label
- 편집 아이콘은 hover/focus 중심

### 18.7 Personal Memo

- Case별·직원별 개인 메모
- 자동 저장
- 기본 visibility = 작성자 본인
- 공식 Fact로 자동 전환 금지
- 필요 시 `내부 공유` 또는 `Fact 후보`로 명시적 전환
- background update로 focus·cursor·draft가 사라지지 않음

### 18.8 Bookmark

- Message/Question/Verification/Task/Report 북마크
- Case별 개인 목록
- 클릭 시 원본 위치로 이동 + Highlight
- 개인 북마크가 기본

---

## 19. Customer Frontend — Customer Case Chat

고객 화면은 은행 화면의 축소판이 아니다.

### 핵심 목표

> 혼자 판단하기 어려운 순간, AI와 대화하며 상황을 확인하고 대응한다.

### 19.1 기본 기능

1. 상황 이해·브리핑
2. 안전 확인·정보 수집
3. 진위 확인·재판단 지원
4. 즉시 행동 안내
5. 은행과 양방향 연결
6. 피해 발생 후 구제 지원

### 19.2 Conversation

- Customer Agent 안내
- 은행 공개 Message
- 구조화 질문
- 고객 답변
- 공개 Verification 결과
- 안전행동
- Recovery 절차 카드
- 첨부파일

### 19.3 Progress — 간결한 기본 화면

고객에게 기본적으로 보여줄 것:

```text
현재 진행 상황

[지금 상태]
기관 절차 확인 중

[완료된 것]
✓ 추가 송금·접촉 중단 확인

[지금 할 일]
증빙 자료를 삭제하지 말고 보관해 주세요.

[담당자에게 확인 요청]   ← 필요한 상태에서만
```

기본 숨김:
- untouched UNKNOWN
- NOT_APPLICABLE
- 아직 고객에게 의미 없는 내부 단계

`답변이 필요한 질문 N건`은 Progress가 아니라 Conversation/Question 영역에 표시한다.

---

## 20. Question Policy

### P0 — 자동 Queue 가능

- 실제 송금 여부
- 개인정보 제공 여부
- 인증정보/OTP 제공 여부
- 원격제어 앱 설치 여부

조건:
- 기존 Fact/Answer로 이미 해결되지 않음
- 의미상 중복 질문 없음
- 고객에게 한 번에 활성 질문 하나

### P1/P2 — 직원 검토 필요

예:
- 사건번호
- 담당 검사/수사관 이름
- 특정 계좌·기관 주장
- 범죄자의 세부 절차 주장

흐름:

```text
AI 후보 생성
→ 직원 검토/선택/수정
→ 고객 전달
→ 고객 답변
→ Fact/Verification 후보 반영
```

---

## 21. Verification Flow

```text
Claim 또는 검증 요청
→ Verification Task 생성
→ Verification Agent / RAG
→ 공식 데이터 조회
→ Evidence 저장
→ Status 판정
→ Bank에 상세 결과
→ 고객에는 승인된 쉬운 요약
```

Status:
- PENDING
- IN_PROGRESS
- VERIFIED
- MISMATCH
- UNVERIFIABLE

---

## 22. Task & AI Recommendation

신규 은행 대응 업무의 Source of Truth는 `tasks`다.

상태:
- TODO
- IN_PROGRESS
- BLOCKED
- COMPLETED
- CANCELLED

규칙:
- 완료 시 결과 필수
- 취소 시 취소 사유 필수
- 다시 진행해도 같은 task_id

### AI에게 추천 받기

```text
은행 직원 클릭
→ BANK_ACTION WorkCard
→ 1~3개 후보
→ 직원 선택
→ 수정
→ 저장
→ AISuggestion + Task 생성
```

AI 추천을 받는 것만으로 Task 생성 금지.

---

## 23. Customer Progress & Recovery

### Progress와 Task는 다르다

- Task = 은행 내부 업무
- CustomerProgress = 고객에게 공개할 실제 진행 상태

Task가 완료됐다고 CustomerProgress가 자동 완료되어서는 안 된다.

### Recovery Mode

진입:
- 고객 `이미 사기 당했어요`
- 은행 담당자가 피해 확인
- 실제 송금 피해 상태 확정

안내 단계:
1. 즉시 연락
2. 증빙 확보
3. 신고 접수
4. 구제 신청

중요:
- Navigator 클릭 = 안내 열기
- 실제 신고/지급정지 완료 아님
- 실제 처리 상태는 담당자 확인/외부 근거가 있어야 변경

---

## 24. Structured Live Case State / AI Case Brief / Final Report

V4의 핵심은 **Live Report가 아니라 최신 Shared Case State**다.

### 24.1 Structured Live Case State

다음 항목은 구조화 데이터가 변경되면 즉시 최신 상태를 보여준다.

- 사건 요약 핵심 필드
- Claim / Demand
- 피해·노출
- 송금 여부
- Verification 상태
- 확인된 Fact
- 확인 필요
- 진행 중 Task
- CustomerProgress
- Timeline/Event

이 업데이트에는 원칙적으로 LLM 재생성이 필요하지 않다.

### 24.2 AI Case Brief

자연어 사건 브리프는 다음 때만 생성/갱신한다.
- 최초 Case 생성
- 고객 P0 핵심 질문 세트 완료
- 중요한 Verification 완료
- 피해 발생/Recovery 진입
- 은행 직원이 `AI 브리프 갱신`을 명시적으로 요청
- 기타 정책으로 정의한 중요 상태 전이

모든 Message·Task·Event마다 Brief를 재생성하지 않는다.

### 24.3 Final Report

Case 종료 시 한 번 전체 Case를 기반으로 생성한다.
- 전체 Shared Case State
- Event Log
- Verification/Evidence
- Task 결과
- 고객 Progress
- 피해/Recovery 결과

필요하면 직원이 Final Report 생성 전에 내용을 검토·확정한다.

### 24.4 제거하는 설계

- polling tick마다 Report 생성
- 모든 Event마다 8개 자연어 Section 재생성
- 읽는 중인 보고서 문장을 계속 자동 교체

서버·AI 비용과 race condition을 줄이고, 사용자가 보는 정보의 안정성을 우선한다.

---

## 25. General Backend Responsibilities

V4 General Backend는 단순 CRUD 서버가 아니라 통합·조정 계층이다.

책임:
- Case 생성·조회·상태전이
- Message/Question/Fact/Verification/Task/Progress CRUD
- Case Projection
- AI API 호출
- Agent Dispatch
- Function/Tool 검증
- Visibility 필터
- Idempotency
- Optimistic concurrency
- Event 발행
- revision/fingerprint 기반 change-aware 동기화
- 선택적 SSE adapter(필수 아님)
- AI Case Brief의 제한적 갱신과 Final Report 생성
- Attachment metadata
- official_contacts 조회

---

## 26. API Design Principles

### 대표 Endpoint

- `POST /api/v4/intake/analyze-text`
- `POST /api/v4/intake/context-event`
- `GET /api/v4/cases`
- `GET /api/v4/cases/{case_id}`
- `GET /api/v4/cases/{case_id}/bundle?view=bank|customer`
- `POST /api/v4/cases/{case_id}/messages`
- `POST /api/v4/cases/{case_id}/questions`
- `POST /api/v4/cases/{case_id}/questions/{question_id}/answer`
- `POST /api/v4/cases/{case_id}/verifications`
- `POST /api/v4/cases/{case_id}/tasks`
- `PATCH /api/v4/cases/{case_id}/tasks/{task_id}`
- `POST /api/v4/cases/{case_id}/ai/work-cards`
- `POST /api/v4/cases/{case_id}/ai/suggestions/{id}/accept`
- `PUT /api/v4/cases/{case_id}/customer-progress/{step}`
- `POST /api/v4/cases/{case_id}/notes`
- `POST /api/v4/cases/{case_id}/bookmarks`
- `GET /api/v4/cases/{case_id}/reports`

Endpoint 이름은 구현 시 기존 AI Engine과의 계약에 맞게 조정할 수 있으나, **Resource 책임과 Single Source 원칙은 바꾸지 않는다.**

---

## 27. Concurrency, History, Idempotency

필수 안전장치:

- 변경 Entity에 `version`
- `expected_version` 불일치 → 409
- Message/Task/Confirmation 등 retry 가능 요청은 `client_request_id`
- 동일 request 재시도 시 중복 생성 금지
- 중요 변경은 Event/History에 기록
- 직원이 확정한 정보는 AI가 덮어쓰지 않음
- 삭제된 직원 항목은 AI가 자동 복원하지 않음
- stale AI result 저장 금지

---

## 28. Frontend State Principles

Server State와 Local Editing State를 명확히 분리한다.

### Server State
- Case
- Message
- Task
- Context
- Verification
- Progress
- Event

### Local State
- 채팅 draft
- 메모 draft
- 편집 중 Task
- Dialog 입력
- 파일 upload 준비 상태
- selection/cursor

### 금지
- Case background update 수신 시 draft 초기화
- revision을 React `key`로 사용해 편집 Component remount
- 동일 데이터인데 Case 전체 객체를 무조건 replace
- AI 응답 대기 동안 사용자 입력 전체 잠금

---

## 29. Design System Principles

목표:
- 금융기관 업무도구
- 차분함
- 빠른 스캔
- 정보 위계
- 실수 방지

색 의미:
- Blue: 기본·정보
- Orange: 확인 필요
- Green: 확인 완료
- Red: 피해·긴급

피해야 할 것:
- 카드 남발
- 중첩 제목
- 같은 의미의 반복 문장
- AI 기술 홍보용 장식
- 과도한 Gradient/Shadow/Animation

---

## 30. V4 Project Structure

권장:

```text
MVP_v4/
  frontend/
    src/
      app/
      pages/
      features/
        case-list/
        conversation/
        case-context/
        questions/
        verification/
        tasks/
        customer-progress/
        recovery/
        notes/
        bookmarks/
        reports/
      api/
      shared/
  backend/
    general_api/
      app/
        api/
        domains/
          intake/
          cases/
          messages/
          context/
          questions/
          facts/
          verifications/
          tasks/
          progress/
          reports/
          events/
          orchestration/
        repositories/
        clients/
  contracts/
  migrations/
  tests/
  docs/
    00_SOURCE_OF_TRUTH.md
    01_PRD.md
    02_ARCHITECTURE.md
    03_DATA_CONTRACTS.md
    04_IMPLEMENTATION_PLAN.md
    05_IMPLEMENTATION_STATUS.md
    06_E2E_SCENARIOS.md
```

기존 AI Engine은 별도 서비스로 재사용하고 V4에서 핵심 로직을 복제하지 않는다.

---

## 31. Development Phases

### Phase 0 — Freeze & Scaffold

- V3 동결
- `MVP_v4` 생성
- 별도 DB 생성
- V4 migration 001 시작
- Frontend/General API health
- Existing AI API health/adaptor 확인
- **V3 AI Engine 재사용 인벤토리 작성: endpoint/module/input/output/cost/side-effect를 `AI_REUSE_MAP.md`에 기록**
- Source of Truth 생성

V4를 구현하기 전에 V3 전체를 다시 설계 검토하지는 않되, **재사용할 AI Engine 경계만 정확히 확인**한다. 확인되지 않은 AI 기능을 새로 구현하거나 Mock으로 대체하지 않는다.

### Phase 1 — Core Contract & Case

- Schema
- Case CRUD
- Event
- Bundle/Projection
- revision/fingerprint 기반 change-aware sync
- Visibility

### Phase 2 — Intake / Case Creation

- 테스트용 Text Input
- ML 분석 연결
- Threshold
- Context Feature Extractor
- Feature-only Reconstruction
- Case 생성

### Phase 3 — Bank Workspace

- Case List
- Conversation
- Case Context
- Task CRUD
- AI task recommendation
- Notes/Bookmarks

### Phase 4 — Customer Workspace

- Customer Chat
- P0 Questions
- P1/P2 전달/답변
- Compact Progress
- Recovery
- Attachment

### Phase 5 — Conversational AI / RAG / Tool / Agent Integration

- Conversational Core LLM
- Role Policy(Customer/Bank)
- Intent routing
- Verification RAG
- Function / Tool Registry
- Customer Agent
- Bank Agent
- Agent handoff
- structured proposals/functions
- AI Evaluation harness

### Phase 6 — Brief & Final Report

- 최초 Case Brief
- 중요 상태 변경 / On-demand Brief refresh
- Final Report
- PDF/Word export if existing engine supports it
- 모든 Event마다 Live Report 자동생성은 구현하지 않음

### Phase 7 — Hardening

- 409
- idempotency
- visibility
- stale AI
- draft/focus
- E2E
- production build

---

## 32. Reuse Matrix — V3 → V4

| 영역 | V4 결정 |
|---|---|
| ML Model/Bundle | 재사용 |
| AI API core | 재사용 우선 |
| RAG corpus/vector DB | 재사용 우선 |
| Prompt/Agent output policy | 재사용·정리 |
| V3 Frontend Components | 원칙적으로 재사용하지 않음 |
| V3 General Backend repositories | 참고만, 새로 구현 |
| V3 DB/migration | 사용하지 않음 |
| V3 legacy actions/task 구조 | 가져오지 않음 |
| V3 UI styles | 참고 가능, 구조 복사 금지 |
| V3 PRD | 역사적 참고자료 |

---

## 33. Acceptance Criteria — Bank

- [ ] Case List가 실제 V4 DB를 사용
- [ ] Case Room의 중앙 Conversation이 업무의 중심
- [ ] 고객/내부/AI 대상이 명확히 구분됨
- [ ] 고객 질문 생성·승인·전달 가능
- [ ] 고객 답변이 같은 Case에 즉시 반영
- [ ] Verification 요청·결과 확인 가능
- [ ] Task 생성·수정·완료·취소·재개 가능
- [ ] AI 업무 추천은 직원 채택 후에만 Task 생성
- [ ] Right Context가 5~10초 내 스캔 가능
- [ ] 개인 메모 입력 중 실시간 Event가 와도 focus/draft 유지
- [ ] 북마크에서 원본 Message로 이동 가능
- [ ] 구조화된 Case State가 변경된 Entity만 갱신되고, AI Case Brief는 정의된 Trigger/명시 요청에서만 갱신

---

## 34. Acceptance Criteria — Customer

- [ ] 고객에게 필요한 안전행동이 첫 화면에서 보임
- [ ] 질문 하나씩 답변 가능
- [ ] 원 질문과 답변이 함께 기록됨
- [ ] P0 질문 중복 없음
- [ ] P1/P2는 직원 승인 전 고객에게 발송되지 않음
- [ ] 고객 자유 메시지가 은행 Shared Case에 반영
- [ ] 공개 Verification 결과를 이해하기 쉬운 문장으로 확인
- [ ] Progress는 지금 상태/완료/지금 할 일 중심
- [ ] untouched UNKNOWN 카드가 기본 노출되지 않음
- [ ] 피해 발생 시 Recovery Mode 유지
- [ ] Recovery 안내 클릭이 실제 조치 완료로 오인되지 않음
- [ ] AI 실패가 고객 메시지 저장을 막지 않음

---

## 35. E2E Demo Scenario

### Scenario A — 예방 성공

1. 테스트 통화 텍스트 입력
2. ML 위험 Threshold 통과
3. Context Feature 추출
4. Feature-only LLM이 Case 재구성
5. Case Room 생성
6. Customer Agent가 P0 안전질문 Queue
7. 고객: 송금 안 함 / 개인정보 일부 제공 / 원격앱 설치 응답
8. Fact 후보·노출 상태 업데이트
9. Verification Agent가 사칭기관 절차 검증
10. Bank Agent가 Brief와 다음 업무 추천
11. 직원이 AI 추천 Task를 수정·채택
12. 고객에게 송금 중단·앱 삭제·공식채널 확인 안내
13. 피해 없음 확인
14. Case Closed
15. Final Report 생성

### Scenario B — 피해 발생

1~9 동일
10. 고객이 이미 송금했다고 응답
11. Case → Recovery Mode
12. 기존 Case 정보로 지급정지/112/피해구제 준비항목 제안
13. 직원이 실제 처리 결과 기록
14. 고객 Progress 갱신
15. Final Report 생성

---

## 36. KPI / Evaluation

MVP 평가 후보:

- Case 생성 성공률
- 최초 Case Brief 생성 시간
- 일상 대화 응답 성공률
- Direct/RAG/Tool/Agent routing 정확도
- 불필요한 AI/Tool 호출률
- RAG 근거 적합도와 출처 일치율
- Function 실행 성공률과 중복 실행률
- 고객 P0 질문 완료율
- 고객 답변 → 은행 화면 반영 지연
- Verification 결과 반영 시간
- 은행 직원이 첫 Task를 실행하기까지 시간
- AI Task 추천 채택/수정/거절 비율
- 중복 질문 발생률
- 고객 화면의 불필요 UNKNOWN 노출 0건
- draft/focus 손실 0건
- visibility 침범 0건
- E2E 성공률

---

## 36.1 Conversational AI Product Principle

CSR의 AI는 메뉴형 자동화 도구만이 아니라 **대화가 기본 인터페이스인 금융 안전 Assistant**다.

- 사용자는 일상적인 문장으로 상황을 설명하거나 질문할 수 있다.
- AI는 Case를 읽고 바로 답할 수 있으면 답한다.
- 공식 근거가 필요하면 RAG를 사용한다.
- 시스템 동작이 필요하면 Function을 호출한다.
- 전문 검증/은행 대응 판단 지원이 필요하면 해당 Agent를 호출한다.
- 사용자는 Agent를 직접 선택할 필요가 없다.
- Tool/Agent 호출 여부는 매번 최소 필요 원칙으로 결정한다.
- 고객에게는 쉬운 말과 안전행동 중심, 은행에는 근거·상태·업무 후보 중심으로 답한다.

**좋은 AI란 많이 호출되는 AI가 아니라, 필요한 순간에 올바른 도구와 근거를 사용하고 그 외에는 자연스럽게 대화하는 AI다.**

---

## 36.2 V4 Build Execution Principle

V4는 문서만 보고 V3 기능을 추측해서 다시 만드는 프로젝트가 아니다.

Codex/개발 에이전트는:
1. V4 문서를 먼저 읽는다.
2. V3는 **AI Engine과 검증된 계약의 재사용 경계만** 확인한다.
3. `MVP_v4`에 신규 Frontend/General Backend/DB를 만든다.
4. 각 Phase마다 build·contract test·핵심 시나리오를 실행한다.
5. 실패한 Phase를 덮고 다음 단계로 진행하지 않는다.
6. 제품 결정이 필요한 blocker가 아니면 과거 PRD를 다시 해석해 구조를 바꾸지 않는다.

---


## 36.3 Hard Runtime Isolation — MVP_v4 단독 실행 원칙

V4의 최종 실행물은 **`MVP_v4` 디렉터리 안에 존재하는 소스·모델·프롬프트·계약·마이그레이션·정적 자산만으로 실행**되어야 한다.

### 절대 금지

다음은 개발 편의를 위해서도 최종 코드에 남겨서는 안 된다.

- `MVP_v3` 또는 다른 sibling 프로젝트의 Python/TypeScript 모듈 import
- `../MVP_v3`, `../../shared` 등 프로젝트 루트 밖 상대경로 참조
- Windows 개발 PC의 `C:\Users\...` 절대경로
- `/mnt/data/...` 같은 임시 실행환경 경로
- `sys.path.append`, `PYTHONPATH` 조작으로 외부 프로젝트 모듈 주입
- V3 디렉터리/파일로 향하는 symlink
- V3의 model, prompt, RAG corpus, migration, static file을 런타임에서 직접 읽는 구조
- Frontend가 V3 API 또는 별도 개발 서버 주소를 직접 호출하는 구조
- V4가 없어도 V3가 살아 있어야 동작하는 hidden runtime dependency

### V3 AI Engine 재사용의 정확한 의미

V3 AI Engine은 **개발 시 읽기 전용 참고·이식 원본**으로만 사용할 수 있다.

재사용하기로 결정한 코드는:
1. 필요한 module/contract/model/prompt를 확인한다.
2. V4의 적절한 위치로 **물리적으로 복사 또는 재구성**한다.
3. import를 V4 내부 경로로 변경한다.
4. model/prompt/RAG config도 V4 내부에서 참조한다.
5. 이후 V4 실행 시 V3 경로 접근이 0건이어야 한다.

즉, “재사용”은 **runtime linkage가 아니라 V4 내부로의 이식**을 의미한다.

### 허용되는 외부 인프라 예외

“V4 폴더 밖 파일 의존 금지”와 “외부 서비스 사용”은 구분한다.

다음은 명시적으로 허용되는 **인프라/네트워크 서비스**다.

- Ubuntu OS / Nginx
- 서버에서 V4 루트에 새로 만든 `.venv`
- MySQL Server
- OpenAI 등 승인된 외부 AI API
- 필요 시 승인된 외부 Vector/Storage 서비스
- Nginx가 `frontend/dist`를 `/var/www/mvp_v4`로 복사해 서비스하는 배포 산출물

단, 외부 서비스 endpoint/credential은 `.env`로 주입하며, 외부 **로컬 코드/파일**을 import하거나 읽는 것은 금지한다.

### Self-containment 증명 테스트

완료 전에 반드시 다음을 통과해야 한다.

1. `MVP_v4`만 별도 임시 디렉터리로 복사한다.
2. V3 및 repository의 다른 폴더가 없는 상태를 가정한다.
3. 새 Python 3.11 venv를 생성한다.
4. `backend/requirements.txt`만으로 dependency를 설치한다.
5. Frontend는 `package-lock.json` 기준 clean install 후 typecheck/build한다.
6. V4 DB migration을 새 DB에 적용한다.
7. General API / AI API health를 실행한다.
8. 핵심 E2E 시나리오를 실행한다.
9. 소스 전체에서 외부 프로젝트 경로, symlink, `sys.path` hack을 검사한다.
10. V3 폴더가 삭제/이름 변경되어도 V4가 동일하게 동작해야 한다.

이 테스트를 통과하지 못하면 V4는 완료가 아니다.

---

## 36.4 AWS Ubuntu EC2 배포 계약

V4는 로컬 개발 후 배포 구조를 다시 뜯어고치는 방식이 아니라, 처음부터 다음 production 구조를 지원한다.

```text
/home/ubuntu/MVP_v4/
  .env
  .env.example
  .venv/

  backend/
    ai_api/
    general_api/
    contracts/
    migrations/
    scripts/
    models/              # 실제 사용하는 ML model
    prompts/             # runtime prompt가 파일이면
    data/
      uploads/
      vector_db/         # local vector store 사용 시
    requirements.txt

  frontend/
    src/
    public/
    dist/
      index.html
      assets/
    package.json
    package-lock.json

  deploy/
    nginx/
    systemd/
    scripts/

  docs/
```

### Python

- Production Python: 3.11
- `.venv`는 AWS에서 `/home/ubuntu/MVP_v4/.venv`로 새로 생성한다.
- 로컬 `.venv`는 복사하지 않는다.
- 모든 Python dependency는 `backend/requirements.txt`로 재현 가능해야 한다.
- 실제 import되는 공용 Python module은 반드시 `MVP_v4/backend` 내부에 포함한다.
- General API와 AI API entrypoint를 문서와 실행 script에서 명확히 고정한다.

권장 process:

```text
AI API      → 127.0.0.1:8101
General API → 127.0.0.1:8100
```

General API가 AI API를 호출할 때는 env 기반 내부 주소를 사용한다.

```text
AI_API_BASE_URL=http://127.0.0.1:8101
```

### Frontend production

Frontend source는 `frontend/src`에서 관리하지만 실제 Nginx serving 대상은 `frontend/dist`다.

배포 전 필수:

```text
npm ci
npm run typecheck
npm run build
```

`frontend/dist` 최소 산출물:

```text
index.html
assets/
```

배포 시 V4 내부에서 생성된 dist를 다음처럼 복사할 수 있다.

```text
/var/www/mvp_v4/
  index.html
  assets/
```

Browser API base는 same-origin `/api`를 기본으로 한다.

```text
Browser
→ Nginx
   ├─ /        → React dist
   └─ /api/*   → General API 127.0.0.1:8100
                    → AI API 127.0.0.1:8101
                    → MySQL
```

Frontend production bundle 안에 다음을 하드코딩하지 않는다.

- `http://localhost:8100`
- `http://127.0.0.1:8100`
- 개발 PC IP
- V3 endpoint
- 개발용 absolute filesystem path

Nginx SPA fallback을 지원한다.

```text
try_files $uri $uri/ /index.html;
```

### Runtime data path

Runtime 생성 파일은 source tree와 구분하되 V4 runtime root 내부를 기본으로 한다.

예:

```text
ATTACHMENT_STORAGE_ROOT=/home/ubuntu/MVP_v4/backend/data/uploads
```

Runtime data는 Git에 commit하지 않는다.

### `.env.example`

`.env.example`에는 실행에 필요한 **환경변수 이름이 빠짐없이** 있어야 하고 비밀값은 포함하지 않는다.

최소 후보:

- APP_ENV
- GENERAL_API_HOST
- GENERAL_API_PORT
- AI_API_HOST
- AI_API_PORT
- AI_API_BASE_URL
- DATABASE_URL 또는 MySQL 개별 변수
- OPENAI_API_KEY
- MODEL 관련 설정
- ATTACHMENT_STORAGE_ROOT
- VECTOR_STORE_PATH / VECTOR DB 설정
- FRONTEND_ORIGIN
- API call/token/cost limit 관련 설정

실제 사용 변수에 맞춰 최종 목록을 코드에서 자동 대조한다.

---

## 36.5 Frontend HTTP IP 호환성 — UUID Hard Contract

V3에서 AWS를 다음과 같이 HTTP IP로 배포했을 때:

```text
http://<EC2_PUBLIC_IP>
```

Component의 `crypto.randomUUID()` 직접 호출이 secure-context 제약으로 실패하여 핵심 흐름이 중단된 경험을 V4에서 반복하지 않는다.

### 절대 규칙

Frontend Component/Hook/API code에서 `crypto.randomUUID()` 또는 `randomUUID()`를 직접 호출하지 않는다.

반드시 공통 helper 하나를 사용한다.

예:

```text
frontend/src/shared/uuid.ts
createUuid()
```

동작 순서:

1. `globalThis.crypto?.randomUUID` 사용 가능 → 사용
2. 아니면 `globalThis.crypto?.getRandomValues` 기반 RFC 4122 UUID v4 생성
3. request ID / message ID / idempotency key는 Backend Contract의 UUID 형식을 유지
4. `Math.random()`만으로 idempotency-critical UUID를 만드는 fallback은 사용하지 않는다.

### 완료 전 검사

- Frontend 전체 `crypto.randomUUID` / `randomUUID` 검색
- 공통 helper 외 직접 사용 0건
- UUID 형식 unit test
- 동일 helper가 request ID, optimistic message ID, idempotency key 등 필요한 위치에서 사용됨
- localhost 테스트
- HTTPS 테스트 가능한 범위
- HTTP IP와 동일한 non-secure-context 조건을 반영한 fallback unit/integration test

V4의 주요 사용자 흐름은 secure context 여부 때문에 깨져서는 안 된다.

---

## 36.6 Deployment Deliverables

최종 V4에는 최소 다음 배포 자산을 포함한다.

- `.env.example`
- `backend/requirements.txt`
- Frontend `package.json` + lockfile
- V4 migration 전체
- 필요한 ML model 파일
- runtime prompt/config
- `deploy/nginx/` example
- `deploy/systemd/` General API / AI API unit example
- `deploy/scripts/` build/start/deploy helper
- `docs/AWS_DEPLOYMENT.md`
- `scripts/verify_self_contained.py` 또는 동등한 검사 script
- `scripts/verify_frontend_uuid_usage.*` 또는 lint/test
- production build와 API health 검증 절차

`AWS_DEPLOYMENT.md`는 최소 다음 순서를 처음부터 끝까지 재현 가능하게 작성한다.

```text
git clone/copy MVP_v4
→ Python 3.11 venv 생성
→ requirements 설치
→ .env 생성
→ DB migration
→ npm ci
→ typecheck
→ build
→ dist 배포
→ AI API 시작
→ General API 시작
→ Nginx 적용
→ health / E2E 검증
```

별도의 V3 파일 복사나 수동 path patch가 이 절차에 포함되면 안 된다.


## SECRET / .env ACCESS — HARD PROHIBITION

개발 Agent(Codex)는 Repository 또는 개발 PC에 존재하는 **실제 Secret 파일을 열거나 읽거나 검색하거나 출력하면 안 된다.**

### 읽기 허용

- `.env.example`
- 코드에 선언된 환경변수 이름(`os.getenv`, `process.env`, Settings schema)
- 공개 설정 문서
- 사용자가 직접 제공한 비밀값이 아닌 변수명·형식 정보

### 읽기 금지

- `.env`
- `.env.local`
- `.env.production`
- `.env.development`
- `.env.*.local`
- 기존 `MVP_v3/.env`
- Secret이 포함될 가능성이 있는 실제 운영 환경파일

금지 행동 예:

```text
cat .env
type .env
Get-Content .env
head/tail/sed .env
grep/search로 .env 값 탐색
Python/Node script로 .env 출력
IDE/Codex file read로 .env 내용 확인
기존 API Key/DB Password/Secret 복사
.env 내용을 로그·문서·응답에 출력
```

`load_dotenv()` 또는 Settings 코드가 **런타임에** `.env`를 읽는 것은 애플리케이션의 정상 동작이다. 그러나 개발 Agent가 파일 내용을 직접 열람하는 것은 금지한다.

필요한 환경변수 이름은 `.env.example`과 코드에서만 파악한다.

실제 Secret 값이 없어서 테스트할 수 없는 단계가 생기면 기존 `.env`를 열어서 해결하지 않는다. 대신 다음 형식으로 보고한다.

```text
[USER_SECRET_REQUIRED]
필요 변수:
- OPENAI_API_KEY
- DATABASE_URL
...
```

V4 `.env.example`에는 변수 이름과 안전한 placeholder만 작성한다. 실제 `.env`는 사용자가 직접 생성·관리한다.

### Secret 파일 탐색 방지

V4 완료 전 다음을 확인한다.

- Codex가 `.env` 내용을 읽는 script/command를 만들지 않았음
- 로그에 secret value가 노출되지 않음
- `.gitignore`에 실제 `.env`와 runtime secret 파일이 포함됨
- `.env.example`만 Git 관리 대상


## V4 초기 폴더 세팅 — 처음부터 이 구조로 시작

V4는 현재 Repository 루트에서 `MVP_v3`와 **형제(sibling) 폴더**로 만든다.

예:

```text
AIXTeamProject2/
├─ MVP_v3/                  # 읽기 전용 참고. 수정 금지.
├─ MVP_v4/                  # 새 V4의 유일한 구현 루트
└─ 기타 기존 프로젝트 파일
```

`MVP_v4` 안의 권장 초기 구조:

```text
MVP_v4/
├─ .gitignore
├─ .env.example
├─ README.md
│
├─ backend/
│  ├─ ai_api/
│  │  ├─ app/
│  │  └─ ...
│  ├─ general_api/
│  │  ├─ app/
│  │  └─ ...
│  ├─ contracts/
│  ├─ migrations/
│  ├─ scripts/
│  ├─ models/
│  ├─ prompts/
│  ├─ data/
│  │  ├─ uploads/
│  │  └─ vector_db/        # local vector store를 쓸 경우
│  └─ requirements.txt
│
├─ frontend/
│  ├─ src/
│  │  ├─ app/
│  │  ├─ pages/
│  │  ├─ features/
│  │  ├─ shared/
│  │  └─ api/
│  ├─ public/
│  ├─ dist/                # build 산출물. 소스가 아님.
│  ├─ package.json
│  ├─ package-lock.json
│  ├─ tsconfig.json
│  └─ vite.config.*
│
├─ deploy/
│  ├─ nginx/
│  ├─ systemd/
│  └─ scripts/
│
├─ docs/
│  ├─ 00_SOURCE_OF_TRUTH.md
│  ├─ 01_PRD.md
│  ├─ 02_IMPLEMENTATION_PLAN.md
│  ├─ 03_IMPLEMENTATION_STATUS.md
│  ├─ 04_DATA_CONTRACTS.md
│  ├─ 05_TEST_SCENARIOS.md
│  ├─ AI_REUSE_MAP.md
│  └─ AWS_DEPLOYMENT.md
│
├─ scripts/
│  ├─ verify_self_contained.*
│  ├─ verify_env_example.*
│  ├─ verify_no_external_runtime_refs.*
│  └─ verify_frontend_uuid_usage.*
│
└─ tests/
```

### 초기 생성 원칙

1. `MVP_v4` 밖에 V4 실행코드를 만들지 않는다.
2. 실제 `.env`는 Agent가 만들거나 읽지 않는다.
3. Agent는 `.env.example`만 만든다.
4. `.venv`는 Repository에 만들지 않아도 되며, 로컬 개발 시에도 필요하다면 `MVP_v4/.venv`로 생성하되 Git에서 제외한다.
5. `node_modules`는 `MVP_v4/frontend/node_modules`에 로컬 생성하고 Git에서 제외한다.
6. V3에서 재사용할 AI 코드·모델·Prompt는 **복사/이식 후 V4 내부 경로로만 import**한다.
7. V4 전용 DB migration은 `MVP_v4/backend/migrations`에서 001부터 새로 시작한다.
8. V3 migration을 V4 DB에 실행하지 않는다.
9. 배포용 Nginx/systemd/script도 V4 내부 `deploy`에 둔다.
10. Phase 0에서 이 구조와 self-containment 검사를 먼저 만든 뒤 기능 구현을 시작한다.


## 36.7 Durable Continuation / Resume Protocol

V4는 단일 Codex 턴이나 단일 사용량 창 안에 완료된다고 가정하지 않는다. 작업이 중단되거나 다른 Codex 세션에서 이어지더라도 **Chat 기억이 아니라 Repository 내부의 상태 문서와 현재 코드**만으로 정확히 재개할 수 있어야 한다.

### 필수 Continuity 파일

`MVP_v4` 생성 직후 다음을 만든다.

```text
MVP_v4/
├─ AGENTS.md
└─ docs/
   ├─ 00_SOURCE_OF_TRUTH.md
   ├─ 01_PRD.md
   ├─ 02_IMPLEMENTATION_PLAN.md
   ├─ 03_IMPLEMENTATION_STATUS.md
   ├─ 04_DATA_CONTRACTS.md
   ├─ 05_TEST_SCENARIOS.md
   ├─ 06_TODO.md
   ├─ 07_WORK_MAPPING.md
   ├─ 08_HANDOFF_CHECKPOINT.md
   ├─ 09_DECISION_LOG.md
   ├─ AI_REUSE_MAP.md
   └─ AWS_DEPLOYMENT.md
```

### 문서 역할

- `AGENTS.md`: 모든 Codex 세션이 반드시 따라야 하는 작업 진입 규칙과 문서 라우팅.
- `02_IMPLEMENTATION_PLAN.md`: Phase, 작업 ID, 의존성, 완료 조건, 테스트 Gate.
- `03_IMPLEMENTATION_STATUS.md`: 현재 실제 구현 상태. `PLANNED / IN_PROGRESS / BLOCKED / DONE / VERIFIED`.
- `06_TODO.md`: 아직 해야 할 원자 단위 작업 목록과 우선순위.
- `07_WORK_MAPPING.md`: 작업 ID ↔ 수정 파일 ↔ API ↔ DB Entity ↔ 테스트 ↔ 의존성 매핑.
- `08_HANDOFF_CHECKPOINT.md`: 중단 직전 상태를 다음 세션이 즉시 이어받기 위한 단일 체크포인트.
- `09_DECISION_LOG.md`: 구현 중 확정한 구조 변경과 이유. 과거 결정을 다음 세션이 다시 뒤집지 않도록 기록.

### 작업 ID

모든 구현 작업은 고유 ID를 갖는다.

예:

```text
P0-001 V4 skeleton
P0-002 AI reuse map
P1-001 Case schema
P1-002 Case create API
P2-001 ML intake adapter
P3-004 Bank task composer
```

TODO, Status, Mapping, Handoff에서 같은 ID를 사용한다.

### 작업 시작 전

Codex는 매 세션/재개 시 구현을 시작하기 전에 다음 순서로 확인한다.

```text
1. AGENTS.md
2. docs/00_SOURCE_OF_TRUTH.md
3. docs/03_IMPLEMENTATION_STATUS.md
4. docs/06_TODO.md
5. docs/07_WORK_MAPPING.md
6. docs/08_HANDOFF_CHECKPOINT.md
7. git status / 현재 diff
8. 필요한 범위의 코드와 테스트
```

Chat의 이전 설명만 믿고 구현하지 않는다.

### 작업 중 업데이트 규칙

원자 작업 하나를 시작할 때:

- `03_IMPLEMENTATION_STATUS.md` → 해당 Task `IN_PROGRESS`
- `08_HANDOFF_CHECKPOINT.md` → `CURRENT_TASK` 갱신

구현 중 파일 범위가 달라지면:

- `07_WORK_MAPPING.md` 즉시 수정

작업 하나가 끝나면:

- 실제 변경 파일 기록
- 실행한 test/command 기록
- pass/fail 기록
- 남은 문제 기록
- `06_TODO.md` 갱신
- `03_IMPLEMENTATION_STATUS.md` 갱신
- `08_HANDOFF_CHECKPOINT.md` 갱신

즉, 문서 갱신을 마지막에 한 번 몰아서 하지 않는다.

### Handoff Checkpoint 최소 형식

```text
LAST_UPDATED:
CURRENT_PHASE:
CURRENT_TASK:
CURRENT_STATUS:

LAST_COMPLETED:
- ...

FILES_CHANGED:
- ...

COMMANDS_RUN:
- command → PASS/FAIL

KNOWN_GOOD_STATE:
- 마지막으로 검증된 동작

INCOMPLETE_CHANGES:
- 파일 / 함수 / 이유

NEXT_EXACT_STEPS:
1. ...
2. ...
3. ...

BLOCKERS:
- ...

DO_NOT_REPEAT:
- 이미 끝난 audit/decision/test

SOURCE_OF_TRUTH_CHANGES:
- 없음 / Decision ID
```

### 중단/사용량 부족 대비

사용량이 부족하거나 큰 다음 작업을 안전하게 끝낼 수 없다고 판단하면:

1. 새 대규모 작업을 시작하지 않는다.
2. 현재 원자 작업을 가능한 clean state까지 마친다.
3. 테스트를 실행한다.
4. Continuity 문서를 모두 갱신한다.
5. `08_HANDOFF_CHECKPOINT.md`에 다음 정확한 시작점을 기록한다.
6. 부분 구현이 남았다면 파일/함수/미완료 부분을 구체적으로 기록한다.

### 재개 프로토콜

다음 Codex 세션은 “처음부터 다시 분석”하지 않는다.

```text
Repository 확인
→ Continuity 문서 읽기
→ git status/diff 확인
→ 마지막 Known Good test 확인
→ 미완료 변경의 일관성 검사
→ NEXT_EXACT_STEPS부터 계속
```

현재 코드와 Handoff가 충돌하면 먼저 실제 코드를 검증한 뒤 Status/Handoff 문서를 수정하고 진행한다.

### Git Checkpoint

가능하면 Phase Gate 또는 큰 기능 단위가 검증된 시점에 **local checkpoint commit**을 사용할 수 있다.

- 자동 push는 하지 않는다.
- 실제 Secret을 commit하지 않는다.
- 사용자가 Git commit을 원하지 않는 환경이면 강제하지 않고 상태 문서 + diff로 대체한다.

### 완료 조건

새 Codex 채팅에서 이전 대화 내용을 전혀 모른다고 가정해도 `MVP_v4`와 위 Continuity 문서만 읽고 현재 작업 위치와 다음 작업을 정확히 설명하고 이어서 구현할 수 있어야 한다.

## 37. Source of Truth Policy

V4에서는 아래 우선순위를 따른다.

1. `MVP_v4/docs/00_SOURCE_OF_TRUTH.md`
2. 승인된 V4 PRD
3. V4 Data Contracts / Architecture
4. V4 실행 코드
5. V4 Implementation Status
6. V3 PRD/PPT/코드
7. 과거 작업로그

중요:
- V3 문서를 읽었다는 이유로 V4 구조를 V3로 되돌리지 않는다.
- V4 문서와 구현이 충돌하면 임의 수정하지 말고 Conflict를 기록한다.
- V3 전체 폴더를 “재사용” 명목으로 복사하지 않는다.

---

## 38. Definition of Done

V4 MVP는 다음이 모두 충족될 때 완료다.

- [ ] V4가 V3와 독립적으로 실행됨
- [ ] V4 별도 DB와 migration 사용
- [ ] 테스트 입력 → ML → Feature → Case 생성 완전 동작
- [ ] 원문을 Case DB에 저장하지 않는 경계 검증
- [ ] Feature Event 직접 입력 경로 존재
- [ ] Bank/Customer가 하나의 Shared Case를 사용
- [ ] General Backend만 AI Engine을 호출
- [ ] Orchestrator가 Event 기반으로 필요한 Agent만 호출
- [ ] Agent 결과가 구조화된 Proposal/Command로 검증됨
- [ ] 은행 Chat-first 업무 가능
- [ ] 고객 Chat-first 상담 가능
- [ ] Verification, Task, Progress, Recovery 동작
- [ ] 구조화 Shared Case State가 변경된 Entity 중심으로 갱신
- [ ] AI Case Brief는 최초 생성·중요 상태 변경·명시 요청에서만 갱신
- [ ] change-aware polling 또는 선택적 SSE로 draft를 훼손하지 않는 동기화 구현
- [ ] draft/focus 안정성 검증
- [ ] expected_version / idempotency / visibility 검증
- [ ] 실제 데모 Scenario A/B 통과
- [ ] Frontend production build 통과
- [ ] Backend/AI contract tests 통과
- [ ] Console 주요 Error 0
- [ ] 주요 Mock/TODO 0 또는 명시적 Non-goal 표시

---

## 39. Final Product Principle

CSR V4는 “AI Agent가 여러 개 있는 서비스”로 보여서는 안 된다.

사용자가 느껴야 하는 것은 다음이다.

> **하나의 사건에서 지금 무엇이 일어나고 있는지, 무엇이 확인됐는지, 무엇을 더 확인해야 하는지, 지금 무엇을 해야 하는지가 바로 보이고, 고객과 은행이 같은 Case를 통해 AI의 도움을 받아 함께 대응하고 있다.**

그리고 기술적으로는:

> **Case-first · Change-aware · Conversational AI · Tool-aware Agents · Human-in-control · Privacy-by-role · Single Source of Truth**

을 V4의 최종 설계 원칙으로 한다.
