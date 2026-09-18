# 은행 화면 기준 Context Pipeline 전체 점검 및 개선 개발 계획

작성일: 2026-09-18  
점검 기준 브랜치: `v3.1-ham`  
점검한 GitHub 기준 커밋: `7a6fbfd9c1158a25ce44373f107f1e9d509f6f1c`  
점검 범위: **은행 화면 > 중앙 채팅 / 은행 화면 > 우측 사건 맥락 패널**을 기준으로 입력 → 세분화 → Fact → 문장화 → 화면 반영 흐름을 전체적으로 점검한다.

> 중요: 이 문서는 A/B/C 담당 구분이 아니라 **사용자가 실제로 보는 화면 영역과 데이터 흐름 기준**으로 작성한다.  
> 또한 GitHub에 push된 `v3.1-ham` 상태를 기준으로 점검했으며, 로컬 PC의 아직 push되지 않은 working tree 변경은 이 점검에서 직접 확인할 수 없다.

---

## 1. 결론 요약

현재 시스템은 **처음 Case를 생성할 때의 통화/STT 분석 경로**와 **Case 생성 후 채팅 메시지를 주고받을 때의 Message → Fact 경로**가 완전히 같은 수준의 Context Pipeline을 사용하지 않는다.

### 처음 Case 생성 시

현재 실제 흐름은 대체로 다음 수준까지 연결되어 있다.

```text
통화/STT 원문
→ Event + 기존 ML 분석
→ Context Feature
→ Semantic Atom
→ observed_terms / lexical·pragmatic feature
→ Semantic Relation / Context Signal / Episode / Action Group
→ privacy-safe Diagnosis 저장
→ Atom 기반 Fact candidate
→ Context V2 PROPOSED Fact
→ Grounded Statement
→ 우측 Context Panel
```

즉 **초기 Case 생성 경로는 세분화 작업이 실제 Backend까지 상당 부분 적용되어 있다.**

### Case 생성 후 채팅 시

현재 실제 흐름은 다르다.

```text
고객/은행 직원 Chat Message
→ Message DB 선저장
→ durable extraction job
→ 별도 ContextFactExtractionService
→ 문자열/정규식 기반 FactProposal
→ Context V2 PROPOSED Fact
→ Context Panel
```

이 경로는 현재 **초기 통화 분석에서 사용하는 Semantic Atom / observed_terms / Relation / Context Signal 체계를 그대로 거치지 않는다.**

따라서 현재 가장 큰 구조적 문제는:

> **초기 통화는 High-Fidelity Semantic Pipeline을 타는데, 이후 채팅은 더 단순한 별도 Fact extractor를 타고 있다.**

이 때문에 같은 의미의 입력이라도 처음 Case 생성 시와 채팅 중 입력 시 정보의 세분화 수준, 불확실성 보존 수준, 문장화 품질이 달라질 수 있다.

---

# 2. 우리가 최종적으로 원하는 하나의 흐름

입력 출처가 달라도 **Context를 만드는 핵심 의미 처리 규칙은 최대한 동일해야 한다.**

단, 통화에는 ML이 적용되고 채팅에는 ML을 적용하지 않는다.

## 2.1 초기 통화/STT

```text
통화 원문
    ↓
Event / Frozen ML Branch
    ↓
Semantic Atom
    ↓
Observed Terms / Expression Feature
    ↓
Relation / Context Signal
    ↓
Semantic Audit
    ↓
Fact Proposal
    ↓
Canonical Context V2 Fact
    ↓
Fine-Grained Grounded Statement
    ↓
우측 Context Panel 현재 상태
    +
중앙 채팅 Analysis Snapshot
```

## 2.2 고객/직원 채팅

```text
Chat Message DB 선저장
    ↓
Context Semantic Extraction
    ↓
Semantic Atom
    ↓
Observed Terms / Expression Feature
    ↓
필요한 Relation / Context Signal
    ↓
Semantic Audit
    ↓
Fact Proposal
    ↓
Canonical Context V2 Fact
    ↓
Fine-Grained Grounded Statement
    ↓
우측 Context Panel 현재 상태 갱신
    +
중앙 채팅 Context Update Snapshot
```

### 절대 유지할 원칙

- 채팅은 **ML 입력으로 보내지 않는다.**
- 원본 Message 저장 성공 후 extraction을 수행한다.
- extraction 실패가 Message 저장을 rollback하지 않는다.
- 통화 원문은 장기 저장하지 않는다.
- 채팅 원문은 기존 메시지 정책 범위에서 저장할 수 있지만, Context Fact는 구조화 의미 중심으로 저장한다.
- AI가 만든 Fact는 `PROPOSED`로 시작한다.
- 직원이 확인하기 전 `CONFIRMED`로 자동 승격하지 않는다.
- 우측 패널이 **현재 canonical state**, 중앙 채팅은 **시간순 변화 기록** 역할을 갖는다.

---

# 3. 화면 영역 1 — 은행 화면 > 중앙 채팅 점검

## 3.1 현재 실제로 보이는 것

현재 `CaseRoomPage.tsx`는 중앙 영역에 `SharedConversation`을 사용한다.

중앙에서는 현재 다음이 보인다.

- 상단 AI BRIEF
- 고객/은행/AI Message
- 고객 확인 질문/답변
- 기관 확인 카드
- 대응 업무 기록
- 최종 보고서
- 전체 기록 모드에서 일부 event

상단 AI BRIEF는:

```text
ContextPanelV3
→ SUMMARY Section
→ onSummaryChange
→ CaseRoomPage.contextSummary
→ SharedConversation.latestSummary
→ AI BRIEF
```

흐름으로 연결되어 있다.

즉 **우측 Context Panel의 Summary가 중앙 상단 Brief에 연결되는 것은 실제 구현되어 있다.**

---

## 3.2 현재 부족한 점

### GAP-CENTER-01 — 세분화 분석 결과 자체는 중앙 채팅에 보이지 않는다

현재 `SharedConversation.tsx`에는 다음을 직접 보여주는 전용 카드가 없다.

- Semantic Atom
- observed_terms
- 세분화된 Fact 변화
- 새로 추가된 Context Fact
- 어떤 문장에서 어떤 Context가 갱신되었는지
- “이번 입력으로 사건 맥락이 이렇게 바뀌었다”는 분석 Snapshot

현재 A 문서 일부에는 중앙 `analysis-result created` 카드에서 의미 피처를 보여준다고 기록되어 있지만,
실제 점검한 `SharedConversation.tsx` 기준으로는 **독립적인 세분화 Analysis Result Card 렌더링 경로를 확인하지 못했다.**

따라서 문서와 실제 Frontend 사이에 상태 표현 차이가 존재한다.

### 현재 판정

**PARTIAL / 문서-코드 재확인 필요**

---

### GAP-CENTER-02 — 중앙 AI BRIEF는 세부 Fact 목록이 아니다

현재 AI BRIEF는 사건 요약이다.

즉 다음과 같은 상세 항목:

- 상대방이 검찰을 사칭
- 상대방이 수사관이라고 주장
- 500만원 송금 요구
- 가족에게 알리지 말라고 요구
- “당장” 처리 요구
- OTP 제공 요구

를 모두 하나씩 보여주는 구조가 아니다.

이는 오류라기보다 Summary 역할상 자연스럽다.

따라서 상세 정보를 중앙 Brief에 억지로 모두 넣는 방향보다는:

> **AI BRIEF = 현재 사건 요약**  
> **Context Update Card = 새로 추가/변경된 세부 Fact**  
> **우측 Context Panel = 현재 전체 canonical state**

로 역할을 분리하는 것이 적절하다.

---

### GAP-CENTER-03 — 채팅 입력 후 Context 변화가 사용자에게 명시적으로 보이지 않는다

현재 Message를 보내면:

1. Message는 즉시 중앙 채팅에 표시
2. 서버에 저장
3. Background extraction 실행
4. Context Fact 생성
5. polling/context revision으로 우측 Panel 갱신

구조다.

하지만 직원은 중앙 채팅만 봤을 때:

> “내가 방금 입력한 문장에서 어떤 사실이 추출되어 사건 맥락에 반영됐는지”

바로 알기 어렵다.

### 개선 목표

채팅 extraction 완료 후 중앙 Timeline에 read-only 카드 추가:

```text
AI 사건 맥락 업데이트

새로 확인이 필요한 정황 3건

- 상대방이 OTP 제공을 요구한 정황입니다.
- 상대방이 가족에게 알리지 말라고 요구한 정황입니다.
- 상대방이 500만원 송금을 요구한 정황입니다.

[사건 맥락에서 확인]
```

이 카드는 새로운 source of truth가 아니다.

반드시 canonical Fact ID / revision을 참조한 **Snapshot Projection**이어야 한다.

---

# 4. 화면 영역 2 — 은행 화면 > 우측 사건 맥락 패널 점검

## 4.1 실제 연결 상태

우측 패널은 실제로 `ContextPanelV3`가 기본 렌더링되고 있다.

Frontend:

```text
CaseRoomPage
→ ContextPanelV3
→ GET /api/cases/{case_id}/context-v2/panel
→ 7개 Section
```

현재 7개 Section:

1. 현재 사건 요약
2. 피해·노출
3. 사칭·접촉 정보
4. 사기 정황
5. 사실·확인 현황
6. 담당자 조치 및 결과
7. 고객 공유 결과

Backend `panel.py`도 같은 7개 Section을 조립한다.

따라서 **우측 Context Panel 자체의 API ↔ Frontend 연결은 실제 구현되어 있다.**

---

## 4.2 Frontend가 상세 문장을 다시 뭉뚱그리지는 않는다

`sections.tsx`에서 Fact는 Backend가 내려준 `item.display_value`를 `FactRow`로 표시한다.

즉:

```text
세밀한 문장이 Backend에서 내려옴
→ Frontend가 다시 요약함
```

구조가 아니다.

따라서 우측 패널에:

> “상대방이 송금·이체를 요구한 정황입니다.”

같은 넓은 문장이 보인다면,
가장 먼저 확인할 곳은 Frontend CSS/렌더링이 아니라:

- 어떤 Fact가 생성되었는가
- Fact에 STRUCTURED_ATOM이 연결되었는가
- `grounded.py`가 supporting Atom을 찾았는가
- legacy broad Fact가 같이 살아 있는가

이다.

### 현재 판정

**Frontend Projection = CONNECTED**  
**Content Fidelity = Source Fact 품질에 따라 PARTIAL**

---

# 5. 초기 Case 생성 경로 상세 점검

## 5.1 통화 분석 세분화 — 적용됨

실제 Diagnosis 경로에는 다음이 존재한다.

- Event / Window ML
- Case Context Features
- Semantic Atom
- observed_terms
- speech_form_codes
- Relation
- Context Signal
- Conversation Episode
- Action Group
- Entity Registry
- Semantic Audit / targeted re-extraction

즉 사용자가 기대하는:

> “입력 내용을 피처·키워드·행동·관계 등으로 세부 분리한다”

는 방향은 **초기 통화 분석에서는 실제 코드에 구현 중이며 상당 부분 연결되어 있다.**

---

## 5.2 Case 저장 — privacy-safe 구조 사용

Case 저장 경계에서:

- `input_text = ""`
- raw transcript 비보관
- privacy-safe Diagnosis 저장
- semantic_atoms 등 additive 구조 저장

방향이 적용되어 있다.

---

## 5.3 Initial Fact seed — 세분화 Atom 사용됨

Case가 생성된 뒤 `seed_initial_context_facts()`가 실행된다.

현재 이 함수는:

- transfer status
- amount
- context feature
- legacy grouped claims/demands/tactics
- Semantic Atom별 Fact candidate

를 함께 생성한다.

특히:

```python
project_semantic_atoms_to_fact_candidates(diagnosis_atoms)
```

가 실제 연결되어 있으므로,
**Semantic Atom → Context Fact → 우측 패널 흐름은 코드상 연결되어 있다.**

---

## 5.4 문제 — Legacy broad candidate와 Fine-Grained candidate가 동시에 존재

현재 초기 seed는 호환성을 위해 기존 grouped candidate를 유지하면서
Atom별 Fine-Grained candidate를 추가한다.

따라서 같은 사건에서:

```text
Broad Fact
“외부 연락 제한”

Fine-Grained Fact
“가족에게 알리지 말라고 요구”

Fine-Grained Fact
“은행에 연락하지 말라고 요구”
```

가 같이 존재할 수 있다.

Panel dedupe가 Atom ID를 포함하도록 개선됐지만,
Broad Fact와 Atom-backed Fact가 완전히 같은 semantic identity가 아니면 둘 다 보일 수 있다.

### 개선 필요

Atom-backed Fine-Grained Fact가 존재하는 경우:

- 같은 의미의 legacy grouped Fact는 production panel에서 숨기거나
- compatibility source로만 유지하거나
- explicit `LEGACY_GROUPED` source로 구분

해야 한다.

DB/history를 삭제할 필요는 없다.

---

# 6. 채팅 Message 경로 상세 점검 — 현재 가장 중요한 문제

## 6.1 Message 저장 순서는 정상

현재 POST Message 흐름:

```text
Message append/commit
→ enqueue_context_extraction
→ background process
```

이다.

따라서 AI extraction 실패가 Message 저장을 rollback하지 않는 기존 원칙은 유지되고 있다.

---

## 6.2 그러나 Chat Context 추출은 A Semantic Pipeline과 별도다

현재 `process_message_context_extraction()`은:

```text
Message
→ ai_client.extract_context_facts()
→ ContextFactExtractionService
→ FactProposal
→ Context V2 Fact
```

경로를 사용한다.

실제 `ContextFactExtractionService`는 현재:

- 정규식
- 문자열 포함 검사
- amount heuristic
- 기관/OTP/앱/긴급성 keyword rule

중심의 bounded extractor다.

즉 채팅 입력은 현재:

```text
Message
→ Semantic Atom
→ observed_terms
→ Relation
→ Context Signal
→ Audit
→ Fact
```

를 거치지 않는다.

### 현재 판정

**INITIAL CALL PIPELINE = HIGH-FIDELITY STRUCTURED**

**CHAT MESSAGE PIPELINE = LOWER-FIDELITY PARALLEL PATH**

이 이중 경로를 통합하는 것이 가장 중요한 다음 개선이다.

---

# 7. 실제 의미 변질이 생길 수 있는 이유

현재 Chat extractor에는 다음 식의 판정이 있다.

```text
“알려줬”
“전달했”
“제공했”
→ supplied
```

따라서:

> “OTP를 알려줬는지도 아직 확인하지 못했어요.”

에도 문자열 `알려줬`이 포함되어
잘못하면:

```text
OTP EXPOSED
```

로 추출될 수 있다.

이는 이전 runtime lineage 점검에서 실제로 관측한:

```text
고객 원문:
OTP를 알려줬는지도 아직 확인하지 못했어요.

Context Fact:
OTP·인증정보를 전달함
```

문제와 구조적으로 일치한다.

따라서 이 문제는 Frontend 문제가 아니다.

핵심 원인은:

> 채팅이 Semantic Atom의 action_state / polarity / modality / unknown contract를 거치지 않는 별도 단순 extractor를 사용한다는 점

이다.

---

# 8. Grounded Statement의 현재 적용 수준

현재 `grounded.py`에는 이미 다음이 구현되어 있다.

- supporting `STRUCTURED_ATOM` 조회
- observed term 사용
- REQUESTED / INSTRUCTED 구분
- CUSTOMER_REPORTED_COMPLETED 구분
- UNKNOWN / MISSING
- NEGATIVE / CONDITIONAL
- communication control 세분화
- requested amount / actual amount
- safe account
- urgency observed term
- Fact ↔ Atom slot alignment validation
- semantic broadening 검증
- Relation 없는 임의 인과 결합 차단

따라서 **Atom-backed Fact는 지금 목표로 하는 세밀한 문장화 방향을 실제로 타고 있다.**

하지만 supporting Atom이 없는 Fact는 broad fallback을 사용한다.

예:

- “송금·이체를 요구한 정황”
- “가족·은행 등 외부에 알리지 않도록 요구”
- “외부 연락이나 주변 상의를 제한한 정황”
- “긴급 처리를 재촉하거나 압박한 정황”

따라서:

> **우측 패널 문장화 품질을 더 올리려면 Template만 고칠 것이 아니라, Fact가 STRUCTURED_ATOM lineage를 갖도록 만드는 것이 우선이다.**

---

# 9. 중앙 채팅과 우측 패널의 최종 역할 정의

두 화면에 같은 정보를 똑같이 복제하지 않는다.

## 중앙 채팅

역할:

> “언제 어떤 입력·판단·업무 변화가 발생했는가”

시간축 중심.

표시 대상:

- 고객/직원 원문 메시지
- AI 답변
- 질문/답변
- 기관 확인
- 업무
- **Context Update Snapshot**
- Initial Analysis Snapshot

### Context Update Snapshot 원칙

- canonical Fact를 참조
- 새로 추가/변경된 Fact만 표시
- read-only
- Fact ID/revision 연결
- “사건 맥락에서 확인” 이동 가능
- 내부 Atom code dump 금지
- 원문 재복원 금지

---

## 우측 Context Panel

역할:

> “현재 이 사건에서 무엇을 알고 있으며 무엇이 아직 미확인인가”

현재 상태 중심.

표시 대상:

- 현재 유효한 canonical Fact
- PROPOSED / CONFIRMED 상태
- Verification
- Task
- 고객 공유 결과

### 원칙

- 동일 의미의 broad legacy row와 fine-grained row 중 fine-grained 우선
- one Fact / one Statement
- 다중 금액/다중 요구/다중 통제 separate row
- evidence/lineage 유지
- 수정/확정/제외는 우측 패널에서 수행

---

# 10. 목표 통합 아키텍처

## 10.1 Source Adapter만 다르게 하고 Semantic Core는 공유

```text
                       ┌─ Call/STT Adapter
Source Input ──────────┤
                       └─ Chat Message Adapter
                                │
                                ▼
                       Semantic Extraction Core
                                │
                 ┌──────────────┼──────────────┐
                 ▼              ▼              ▼
          Semantic Atom   observed_terms   Expression Feature
                 │
                 ▼
          Semantic Audit
                 │
                 ▼
        Relation / Context Signal
                 │
                 ▼
          Fact Proposal
                 │
                 ▼
        Context V2 Canonical Fact
                 │
                 ▼
       Fine-Grained Grounded Statement
              ┌──┴──┐
              ▼     ▼
        중앙 Snapshot   우측 Panel
```

### ML 예외

Call/STT만 기존 Frozen ML branch를 탄다.

Chat Message는 ML에 넣지 않는다.

---

# 11. 개발 Phase 제안

## Phase 0 — Runtime Baseline 고정

목적: 수정 전에 실제 화면/DB/API 상태를 증거로 남긴다.

### 해야 할 것

- 신규 Case 1건 생성
- 동일 Case에서 고객 Chat 입력
- 은행 직원 Chat 입력
- 각 단계의 다음 결과 저장
  - Diagnosis JSON
  - Semantic Atom
  - Context Fact
  - Panel API
  - 중앙 화면 Screenshot
  - 우측 Panel Screenshot

### 반드시 같은 사실을 ID로 추적

```text
source turn/message
→ atom_id
→ fact_id
→ panel item_id
→ central snapshot item
```

### 상태

**NOT RUN — 실제 브라우저 E2E 필요**

---

## Phase 1 — Chat Message Semantic Extraction 통합

### 목표

기존 Chat `ContextFactExtractionService`를 primary semantic engine으로 유지하지 않는다.

### 개선 방향

```text
현재
Message → heuristic FactProposal

목표
Message → Semantic Atom → Audit → FactProposal
```

### 구현 시 확인할 파일

- `backend/ai_api/app/domains/case_support/context_fact_extraction_service.py`
- `backend/ai_api/app/domains/diagnosis/semantic_atoms.py`
- `backend/ai_api/app/domains/diagnosis/lexical_cues.py`
- `backend/ai_api/app/domains/diagnosis/relations.py`
- `backend/contracts/diagnosis.py`
- Context extraction internal contract
- `backend/general_api/app/main.py::process_message_context_extraction`

### 원칙

- 기존 Message DB 선저장 유지
- 채팅 원문은 Message resource에서만 기존 정책대로 저장
- Fact value에 원문 전체 `text`를 복제하지 않는 방향 검토
- Chat Atom은 `source_message_id`를 가져야 함
- Fact evidence:
  - `MESSAGE`
  - `STRUCTURED_ATOM`
  를 함께 추적 가능하게 함
- 기존 deterministic extractor는 안전 fallback 또는 compatibility path로 축소

---

## Phase 2 — Initial Seed의 Broad Legacy Fact 정리

### 목표

초기 Case에서 Atom-backed 세부 Fact가 이미 존재하는데
같은 뜻의 legacy broad Fact가 추가로 화면에 나오는 문제를 줄인다.

### 구현 원칙

삭제보다 projection policy 변경을 우선한다.

```text
Atom-backed specific Fact 존재
→ 동일 semantic family의 legacy grouped Fact는 패널 표시 우선순위 낮춤
```

### 검증

다음이 동시에 보이면 실패:

```text
외부 연락 제한
가족에게 알리지 말라고 요구
은행에 연락하지 말라고 요구
```

원하는 화면:

```text
가족에게 알리지 말라고 요구한 정황입니다.
은행에 연락하지 말라고 요구한 정황입니다.
```

Broad legacy row는 history/compatibility로만 유지 가능.

---

## Phase 3 — 우측 Panel Fine-Grained Projection E2E

### 목표

Backend에서 생성한 세부 Fact가 실제 화면에 그대로 보이는지 검증한다.

### 확인 항목

- semantic key → 올바른 Section
- Fact 1개 → Row 1개
- Atom별 separate row
- PROPOSED / CONFIRMED badge
- Evidence toggle
- amount summary
- multiple amount
- communication control
- observed term
- UNKNOWN
- NEGATIVE
- correction/supersede
- refresh 후 유지

---

## Phase 4 — 중앙 채팅 Context Update Snapshot

### 목표

중앙 채팅에서 사용자가:

> “방금 입력한 정보가 사건 맥락에 어떻게 반영되었는지”

알 수 있게 한다.

### Initial Analysis Snapshot

Case 최초 생성 시:

```text
AI 분석 결과

위험 신호 및 사건 정황을 구조화했습니다.

사칭·접촉
- 상대방이 검찰을 사칭한 정황입니다.
- 상대방이 수사관이라고 주장한 정황입니다.

상대방 요구
- 상대방이 500만원 송금을 요구한 정황입니다.
- 상대방이 OTP 제공을 요구한 정황입니다.

압박·조작
- 상대방이 ‘당장’ 처리하라고 요구하며 행동을 재촉한 정황입니다.
- 상대방이 가족에게 알리지 말라고 요구한 정황입니다.

6건 · 담당자 확인 필요
[사건 맥락에서 확인]
```

### Chat Context Update Snapshot

채팅 이후:

```text
사건 맥락 업데이트

이번 대화에서 새로 반영된 정황 2건

- OTP 제공 여부는 아직 확인되지 않았습니다.
- 실제 송금액은 고객이 300만원이라고 정정했습니다.

[사건 맥락에서 확인]
```

### 구현 원칙

- Snapshot은 새로운 canonical DB Fact가 아니다.
- canonical Fact delta를 읽어 표현한다.
- 내부 code/confidence는 일반 직원 화면에 노출하지 않는다.
- 중앙 카드에서 확정/미확정을 잘못 표현하지 않는다.
- 같은 카드가 polling 때마다 중복 생성되면 안 된다.

---

# 12. 필수 회귀 시나리오

## Scenario 1 — 세분화 초기 Case

입력 의미:

```text
검찰 사칭
수사관 주장
안전계좌
500만원 송금 요구
OTP 요구
당장 처리 요구
가족 연락 금지
```

기대:

서로 다른 의미가 각각 Atom/Fact/Statement로 유지.

우측 패널:

```text
사칭 기관
- 상대방이 검찰을 사칭한 정황입니다.

사칭 인물·직책
- 상대방이 수사관을 내세운 정황입니다.

상대방 요구
- 상대방이 안전계좌로 500만원 송금을 요구한 정황입니다.
- 상대방이 OTP 제공을 요구한 정황입니다.

압박·조작
- 상대방이 ‘당장’ 처리하라고 요구하며 행동을 재촉한 정황입니다.
- 상대방이 가족에게 알리지 말라고 요구한 정황입니다.
```

---

## Scenario 2 — UNKNOWN 보존

채팅:

```text
OTP를 알려줬는지도 아직 확인하지 못했어요.
```

절대 금지:

```text
OTP·인증정보를 전달함
```

기대:

```text
OTP 제공 여부는 아직 확인되지 않았습니다.
```

---

## Scenario 3 — 요구 vs 실제 행동

채팅:

```text
500만원을 보내라고 했지만 실제로는 300만원만 송금했어요.
```

기대:

```text
요구 금액 = 5,000,000
실제 송금액 = 3,000,000
```

두 Fact를 합치지 않는다.

---

## Scenario 4 — 정정

```text
아까 350만원이라고 했는데 정확히는 300만원입니다.
```

기대:

- 이전 값 history 유지
- 새 값 PROPOSED
- 직원 확정 시 이전 값 SUPERSEDED
- 패널 current state는 300만원

---

## Scenario 5 — 서로 다른 통신 통제

```text
가족에게 말하지 말라고 했어요.
은행에도 연락하지 말라고 했어요.
```

기대:

```text
가족에게 알리지 말라고 요구
은행에 연락하지 말라고 요구
```

별도 Fact/문장.

---

## Scenario 6 — extraction failure

기대:

- Message는 중앙 채팅에 남음
- extraction FAILED 기록
- retry 가능
- 기존 Context Panel은 깨지지 않음

---

## Scenario 7 — 중앙/우측 동일성

같은 Fact가:

```text
중앙 Context Update Snapshot
↔
우측 Context Panel
```

에서 같은 `fact_id / revision / semantic state`를 가리켜야 한다.

문구는 UI 목적에 따라 다를 수 있으나 의미 상태는 같아야 한다.

---

# 13. 현재 진행 상태 Matrix

| 영역 | 현재 상태 | 판정 |
| --- | --- | --- |
| 초기 통화 Event/ML | 구현 | CONNECTED |
| 초기 Semantic Atom | 구현 | CONNECTED |
| observed_terms | 구현 | CONNECTED |
| Relation/Context Signal | 구현 | CONNECTED |
| Semantic Audit | 구현 | CONNECTED |
| 초기 Atom → Fact | 구현 | CONNECTED |
| 초기 Fact → Grounded Statement | 구현 | CONNECTED |
| 우측 Panel API | 구현 | CONNECTED |
| 우측 Panel Frontend | 구현 | CONNECTED |
| 우측 Panel browser E2E | 증거 부족 | NOT VERIFIED |
| 채팅 Message 선저장 | 구현 | CONNECTED |
| 채팅 extraction job | 구현 | CONNECTED |
| 채팅 → Semantic Atom | 미통합 | GAP |
| 채팅 → observed_terms/Relation/Signal | 미통합 | GAP |
| 채팅 → direct FactProposal | 구현 | LEGACY/PARALLEL PATH |
| 채팅 Fact → 우측 Panel | 구현 | CONNECTED, 낮은 fidelity 가능 |
| 중앙 AI Brief | 구현 | CONNECTED |
| 중앙 Fine-Grained Analysis Snapshot | 실제 렌더 경로 확인 안 됨 | GAP / DOC-CODE CHECK |
| 중앙 Chat Context Update Snapshot | 없음 | GAP |
| 중앙 ↔ 우측 same Fact revision E2E | 미검증 | NOT VERIFIED |

---

# 14. 문서와 코드 상태 차이

현재 A 체크리스트에는 다음 항목이 완료로 기록되어 있다.

> 중앙 `analysis-result created` 카드에 직원용 의미 피처 표시

하지만 점검한 현재 Frontend `SharedConversation.tsx`에서는
Semantic Atom/Fact 분석 결과를 별도 카드로 표시하는 전용 컴포넌트/분기를 확인하지 못했다.

따라서 다음 중 무엇인지 실제 브라우저와 최신 로컬 working tree에서 확인해야 한다.

1. GitHub에 아직 push되지 않은 Frontend 변경이 로컬에 존재
2. 과거 카드가 다른 경로에 존재하지만 현재 CaseRoom에서 렌더되지 않음
3. 문서가 실제 구현보다 앞서 완료 처리됨
4. `analysis-result created`가 UI 카드가 아니라 내부 결과/개발자 표현을 뜻함

### 조치

실제 브라우저 E2E 전에 이 항목을 `완료`로 다시 단정하지 않는다.

---

# 15. 개발 우선순위

## P0-1. Chat Semantic Pipeline 통합

가장 먼저 한다.

이 단계가 해결되지 않으면,
초기 Case는 세밀하고 채팅 이후 Fact는 뭉뚱그려지는 구조가 계속된다.

---

## P0-2. Runtime E2E 증거 확보

다음 4개를 한 Case에서 캡처한다.

```text
Input
→ Structured Atom/Fact JSON
→ Panel API
→ Browser
```

초기 생성과 Chat을 각각 수행한다.

---

## P0-3. 우측 Panel broad legacy 중복 제거 정책

fine-grained Fact 우선.

DB history는 유지.

---

## P1-1. 중앙 Context Update Snapshot

우측 canonical state를 복제 저장하지 않고
Fact delta만 중앙 흐름에 Snapshot으로 표시한다.

---

## P1-2. Summary 최신화

현재 Summary는 별도 목적의 압축 view다.

세부 Fact와 혼동하지 않는다.

Summary가 최신 canonical Fact를 반영하는지는 별도 revision 검증한다.

---

# 16. 개발 시 변경 후보 파일

실제 작업 전 다시 코드 검색 후 확정한다.

## Semantic Extraction

- `backend/ai_api/app/domains/case_support/context_fact_extraction_service.py`
- `backend/ai_api/app/domains/diagnosis/semantic_atoms.py`
- `backend/ai_api/app/domains/diagnosis/lexical_cues.py`
- `backend/ai_api/app/domains/diagnosis/relations.py`
- 관련 contracts

## General API

- `backend/general_api/app/main.py`
  - `process_message_context_extraction`
  - `seed_initial_context_facts`
- Context Fact repository

## Projection

- `backend/general_api/app/domains/cases/context_v3/atom_fact_projection.py`
- `backend/general_api/app/domains/cases/context_v3/grounded.py`
- `backend/general_api/app/domains/cases/context_v3/panel.py`

## Frontend 중앙

- `frontend/src/components/SharedConversation.tsx`
- `frontend/src/timeline.ts`
- 필요 시 신규 `ContextUpdateCard`

## Frontend 우측

기본 구조 변경은 최소화한다.

- `frontend/src/context-v3/ContextPanelV3.tsx`
- `frontend/src/context-v3/sections.tsx`

우측 Frontend 자체보다 Backend projection 일관성이 우선이다.

---

# 17. Definition of Done

다음이 모두 만족되어야 “초기 Case + Chat → 세분화 → 문장화 → 화면”이 연결됐다고 판단한다.

- [ ] 초기 통화에서 semantic Atom이 생성된다.
- [ ] 초기 통화 Atom마다 필요한 Fact가 생성된다.
- [ ] 채팅에서도 동일 semantic contract의 Atom이 생성된다.
- [ ] 채팅은 ML에 들어가지 않는다.
- [ ] `UNKNOWN`이 긍정 사실로 변하지 않는다.
- [ ] NEGATIVE가 POSITIVE로 변하지 않는다.
- [ ] REQUESTED가 COMPLETED로 변하지 않는다.
- [ ] 여러 금액이 서로 구분된다.
- [ ] 여러 communication control이 서로 구분된다.
- [ ] observed term이 있는 경우 specificity가 유지된다.
- [ ] 없는 surface 표현을 임의 생성하지 않는다.
- [ ] Atom-backed Fact가 우측 패널에 one Fact / one Statement로 표시된다.
- [ ] broad legacy Fact가 fine-grained Fact와 중복 노출되지 않는다.
- [ ] Fact evidence에서 원 입력 Message 또는 STRUCTURED_ATOM을 추적할 수 있다.
- [ ] 중앙 채팅에서 새 Context 변화가 Snapshot으로 확인된다.
- [ ] 중앙 Snapshot과 우측 Panel이 같은 canonical Fact revision을 참조한다.
- [ ] 새로고침 후 동일 상태를 유지한다.
- [ ] extraction 실패가 Message 저장을 rollback하지 않는다.
- [ ] 고객 화면에 BANK_INTERNAL 구조화 정보가 노출되지 않는다.
- [ ] 실제 브라우저 E2E 증거가 있다.

---

# 18. 이번 점검 최종 판정

## 은행 중앙 채팅

**PARTIAL**

메시지·업무·질문·AI Brief는 잘 연결되어 있다.

하지만:

> “입력 → 세분화 Context → 새로 반영된 의미를 직원이 중앙 흐름에서 확인”

하는 전용 Context Update 표시가 현재 점검한 Frontend에서는 확인되지 않는다.

---

## 은행 우측 패널

**BACKEND/FRONTEND CONNECTED, FIDELITY PARTIAL**

7개 Section과 canonical Fact projection은 실제 연결돼 있다.

초기 Atom-backed Fact는 세밀한 grounded 문장으로 표현할 수 있다.

하지만 채팅에서 생성된 Fact는 Semantic Atom lineage 없이 들어올 수 있어
같은 `grounded.py`를 사용하더라도 broad fallback 문장으로 보일 가능성이 높다.

---

## 전체 Pipeline

**구조는 거의 이어졌지만 입력 출처별 Context extraction 경로가 아직 통일되지 않았다.**

가장 먼저 해결할 사항:

> **Chat Message extraction을 Initial Diagnosis와 같은 High-Fidelity Semantic Context Core에 연결한다.**

그 다음:

> **우측 패널 E2E → 중앙 Context Update Snapshot → 중앙/우측 revision 일치 검증**

순서로 진행한다.

---

# 19. 다음 개발 작업 시작 전 체크

1. 로컬 `v3.1-ham` working tree와 이 문서의 GitHub 점검 기준 SHA 차이를 확인한다.
2. 로컬에 push되지 않은 Context/Frontend 변경이 있으면 먼저 이 문서와 대조한다.
3. 실제 브라우저에서 신규 Case 1건을 만들어 중앙/우측 화면을 캡처한다.
4. 고객 Chat으로 UNKNOWN/정정/다중금액 fixture를 넣는다.
5. API JSON과 화면 결과를 비교한다.
6. 그 결과를 기준으로 Phase 1부터 구현한다.

이 문서는 역할 분담 문서가 아니라 **은행 화면에서 실제 사용자가 보는 결과의 일관성과 Context fidelity를 높이기 위한 통합 개발 기준**으로 사용한다.
