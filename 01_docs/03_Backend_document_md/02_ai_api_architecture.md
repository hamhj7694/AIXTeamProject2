# AI API 구현 구조

> 기준 문서: [개발 구현 체크리스트 | Frontend · Backend API · MySQL](https://app.notion.com/p/3cdc753ff28a81f9b261c9d157543bac?pvs=204)  
> 목적: 일반 Backend가 내부 호출하는 AI 분석 계층의 기능·입출력·연동 흐름을 정의한다.

---

## 1. AI API 역할

AI API는 다음을 담당한다.

1. 텍스트 전체 분석
2. Window/부분 단위 분석
3. Context Feature 추출
4. ML Risk / 분류
5. **Case Report AI — 1개 사건의 LIVE/FINAL 보고서**
6. P0/P1/P2 질문 생성 지원
7. Verification Plan
8. 비정형 답변의 Shared Case 구조화
9. 공식문서 RAG / 공식절차 검증
10. 실시간 STT
11. 음성상담 증분 분석·최종 요약

### 호출 원칙

```text
CSR Frontend
   ↓
일반 Backend
   ↓
AI API
   ↓
ML / LLM / STT / RAG / Agent
   ↓
구조화 JSON
   ↓
일반 Backend
   ↓
MySQL 저장 + Realtime Publish
```

- Frontend가 AI API를 직접 호출하지 않는다.
- AI API가 MySQL을 직접 수정하지 않는다.
- AI 결과는 가능한 한 자유문장만 반환하지 않고 구조화 Schema로 반환한다.
- `case_id`, `segment_id`, `feature`, `risk`, `evidence`, `summary`, `question`, `source` 등을 명시한다.

---

## 2. Text Diagnosis / ML

| Method | Path | 역할 |
|---|---|---|
| POST | `/ai/analyze/text` | 전체 통화 맥락 분석 |
| POST | `/ai/analyze/windows` | 부분·Window 단위 분석 |
| POST | `/ai/features/extract` | Context Feature 추출 |
| POST | `/ai/risk/predict` | ML Risk·분류 결과 생성 |

### 분석 기준

- 전체 단위: “이 통화 전체가 어떤 사건인가?”
- Window 단위: “대화가 진행되면서 어떤 위험신호가 언제 등장했는가?”
- 근거로 Segment / Timestamp / Text Span을 가능한 한 포함한다.

### Context Feature 예시

노션에 정의된 범위를 기준으로:

```text
impersonation
authority
fear
urgency
isolation
money_request
transfer_request
amount
credential/privacy exposure
remote-control context
verification blocking
```

구체 Feature Schema는 모델 구현 시 최종 확정한다.

---

## 3. Case Report AI

### 정의

**Case Report AI**는 하나의 `case_id`에 누적되는 모든 사건 데이터를 종합해:

- **LIVE 사건 보고서**를 계속 갱신하고
- 사건 종료/해결 시 **FINAL 사건 보고서**를 생성한다.

단순 통화 요약이 아니라 **현재 사실·위험맥락·확인상태·조치·남은 과업을 구조화**하는 모델이다.

### API

| Method | Path | 역할 |
|---|---|---|
| POST | `/ai/reports/initialize` | 최초 Case 분석 후 초기 보고서 |
| POST | `/ai/reports/update` | 신규 데이터로 영향받는 LIVE Section만 Delta/Patch 반환 |
| POST | `/ai/reports/finalize` | 전체 Case 이력을 다시 읽어 FINAL 보고서 생성 |

### LIVE Report는 Section 기반으로 관리

LIVE Report를 하나의 긴 자유문장으로 보지 않는다. 내부적으로 안정적인 `section_key`를 가진 조각으로 관리한다.

```text
summary
risk_context
transfer_status
exposure_status
verification_status
current_actions
unresolved_items
next_checks
```

새로운 데이터가 들어왔을 때 AI가 매번 모든 Section을 다시 쓰지 않는다.

```text
새 Event
  ↓
영향 범위 판별
  ↓
변경이 필요한 section_key 선택
  ↓
해당 Section만 재구성
  ↓
Report Patch 반환
```

전체 Refresh가 필요한 경우는 다음처럼 제한한다.

- 최초 Report Skeleton 생성
- Section 간 의미 충돌이 커서 전체 일관성 재검사가 필요한 경우
- 담당자가 명시적으로 전체 Refresh 요청
- FINAL 보고서 생성

### Report Patch 개념 Schema

```json
{
  "case_id": "VP-014",
  "base_report_version": 12,
  "patches": [
    {
      "section_key": "verification_status",
      "operation": "UPSERT",
      "base_section_version": 3,
      "content": {},
      "source_ids": ["ver_18", "rag_ev_33"]
    }
  ]
}
```

- `patches`에 없는 Section은 변경하지 않는다.
- AI API는 DB를 직접 수정하지 않는다.
- Backend가 `base_section_version`을 검증한 뒤 저장한다.
- Patch가 충돌하면 최신 State로 재요청하거나 전체 Refresh를 선택한다.

### Case Report AI 입력

```text
case_id
├─ 최초 입력 통화/STT
├─ analysis_segments
├─ context_features
├─ 고객·은행 messages
├─ P0/P1/P2 질문·답변
├─ voice transcript
├─ verification 결과
├─ RAG / case_evidence
├─ bank actions
├─ recovery state
└─ timeline / case_events
```

### LIVE 보고서 포함 내용

- 현재 사건요약
- 핵심 확인사실
- 사칭 유형
- 심리전략
- 요구행동
- 송금 여부 / 금액
- 개인정보·인증정보·원격제어 노출 상태
- 현재 검증상태
- 최신 변화
- 현재 조치
- 미확인사항
- 다음 확인 필요사항

### FINAL 보고서 포함 내용

- 사건 전체 요약
- 사건 전체 Timeline
- 최종 확인사실
- 피해·거래정보
- 수행한 Verification
- 사용한 공식 근거
- 고객 조치
- 은행 조치
- 결과
- Recovery / 후속조치 상태

### 근거 추적

가능한 경우 보고서 주장마다 다음을 연결한다.

```text
source_type
source_id
segment_id / event_id
evidence
```

### 버전 원칙

```text
LIVE Report Root
├─ summary v2
├─ risk_context v4
├─ transfer_status v3
├─ verification_status v7
└─ current_actions v5

FINAL
├─ Revision 1
└─ Revision 2 (필요한 경우)
```

- LIVE: **Section별 독립 Version**
- 중요 시점에는 선택적으로 전체 LIVE Snapshot을 남길 수 있음
- FINAL: 사건 전체를 다시 읽고 일관성을 검토한 Immutable Revision
- AI API는 Section Patch 또는 FINAL Report JSON을 반환
- 저장·Version·최신본 지정은 일반 Backend + MySQL 담당

### Report JSON 개념 예시

> 아래는 구현용 개념 스키마이며 필드 타입은 최종 API 설계에서 확정한다.

```json
{
  "case_id": "VP-014",
  "report_type": "LIVE",
  "summary": "...",
  "confirmed_facts": [],
  "risk_context": {},
  "transfer_status": {},
  "exposure_status": {},
  "verification_status": [],
  "actions": [],
  "unresolved_items": [],
  "next_checks": [],
  "sources": []
}
```

---

## 4. Question / Verification / Case Structuring

| Method | Path | 역할 |
|---|---|---|
| POST | `/ai/questions/next` | P0 자동질문 또는 P1/P2 질문 후보 |
| POST | `/ai/verifications/plan` | 검증할 주장·주체·방법 제안 |
| POST | `/ai/case/structure` | 비정형 답변을 Shared Case Field로 구조화 |

### 질문과 선택지의 출력 단위

질문 1개와 선택지 목록을 분리 가능한 구조로 반환한다.

```json
{
  "question": {
    "question_id": "q_transfer_status",
    "text": "이미 송금했나요?",
    "priority": "P0",
    "target_field": "transfer_status"
  },
  "options": [
    {"option_key": "A", "label": "아직 송금하지 않았어요", "value": "NOT_SENT"},
    {"option_key": "B", "label": "이미 송금했어요", "value": "SENT"},
    {"option_key": "C", "label": "잘 모르겠어요", "value": "UNKNOWN"}
  ]
}
```

Frontend는 질문 또는 선택지 중 변경된 조각만 교체할 수 있다.

### 질문 정책

- P0는 사전 정의된 표준 안전질문을 우선
- LLM이 제한 없이 임의 질문을 만드는 구조는 사용하지 않음
- P1/P2는 담당자 승인형
- 실제 비밀번호·OTP·보안카드 전체번호·인증코드 등 민감정보 요청 금지

---

## 5. RAG / 공식절차 검증

### API

| Method | Path | 역할 |
|---|---|---|
| POST | `/ai/rag/search` | Case 질문에 맞는 공식문서 Chunk 검색 |
| POST | `/ai/rag/verify-claim` | 상대방 주장과 공식절차 비교 근거 |
| POST | `/ai/rag/response-guide` | 지금 필요한 안전행동의 공식 근거 |
| POST | `/ai/rag/recovery-guide` | 지급정지·신고·후속조치 근거 |
| POST | `/ai/rag/institution-info` | 기관 역할·정상 업무절차 근거 |

### RAG 유형

```text
Verification RAG
└─ 상대방 주장이 공식절차와 맞는가?

Response RAG
└─ 지금 무엇을 해야 하는가?

Recovery RAG
└─ 이미 피해가 발생했다면 어떤 절차인가?

Institution RAG
└─ 어떤 기관이 어떤 역할을 하고 어떻게 확인하는가?
```

### RAG 응답 Metadata

```text
source_id
chunk_id
agency
title
source_url
evidence
retrieval_score
effective_date (가능한 경우)
```

### 원칙

- RAG가 독단적으로 “사기 확정”을 선언하지 않는다.
- 공식절차와 **일치 / 불일치 / 확인 필요**의 근거를 제공한다.
- 전화번호·공식 URL처럼 정확한 단일 값은 RAG/LLM 생성값을 사용하지 않는다.
- 정확값은 일반 Backend가 MySQL `official_contacts`에서 조회한다.

---

## 6. Voice STT / 실시간 상담 분석

### API

| Method | Path | 역할 |
|---|---|---|
| WS | `/ai/stt/stream/:sessionId` 또는 동등 API | 실시간 STT |
| POST | `/ai/voice/analyze-delta` | 신규 Final Transcript Segment 증분 분석 |
| POST | `/ai/voice/summarize` | 상담 종료 후 전체 상담 요약 |

### STT 원칙

- Partial Transcript와 Final Transcript 구분
- DB 저장은 Final Segment 중심
- 가능하면 별도 Audio Track / participant ID로 화자 구분
- Mixed Audio일 때만 Speaker Diarization 사용

### 증분 분석

Final Segment가 들어올 때마다:

```text
Transcript Segment
   ↓
Context Feature 갱신
   ↓
Risk/맥락 변화 확인
   ↓
새로 확인된 사실 추출
   ↓
미확인사항 추출
   ↓
후속질문 후보
   ↓
기존 Case 정보와 충돌/변경 감지
   ↓
일반 Backend 반환
```

이 결과는 Case Report AI LIVE 갱신 Trigger가 될 수 있다. 이때 Report AI는 전체 보고서가 아니라 영향받는 Section만 Patch하는 것을 기본으로 한다.

---

## 7. AI API 공통 응답 원칙

- 구조화 JSON 우선
- 모든 결과에 `case_id`
- Segment 기반 결과는 `segment_id`
- 근거가 있는 판단은 `evidence`
- RAG 결과는 source metadata 포함
- 모델 오류 시 명시적 Error Code
- JSON Schema Validation 가능하게 설계
- AI 모델의 결과를 DB 진실값과 동일시하지 않음
- 일반 Backend가 최종 병합·저장·배포

---

## 8. 모델/서비스별 구현 단위

```text
AI API
├─ Diagnosis Service
│   ├─ Full Text Analyzer
│   ├─ Window Analyzer
│   ├─ Feature Extractor
│   └─ Risk Model
│
├─ Case Intelligence Service
│   ├─ Case Structurer
│   ├─ Question Planner
│   ├─ Verification Planner
│   └─ Case Report AI
│
├─ Voice Intelligence Service
│   ├─ Streaming STT
│   ├─ Speaker Handling
│   ├─ Delta Analyzer
│   └─ Consultation Summarizer
│
└─ Knowledge / RAG Service
    ├─ Retriever
    ├─ Verification RAG
    ├─ Response RAG
    ├─ Recovery RAG
    └─ Institution RAG
```

위 서비스 분할은 구현 조직화를 위한 문서 구조이며 실제 프로세스/컨테이너 분리는 개발 환경에 맞게 결정한다.

---

## 9. 아직 확정이 필요한 항목

- 실제 STT Provider
- ML 모델 Serving 방식
- LLM Provider / Model
- Embedding Model
- Vector DB 제품
- Chunk 크기·Overlap
- RAG Retrieval Top-K / Reranking
- Report JSON 최종 Schema
- 모델 Timeout / Retry
- 평가 지표 및 테스트셋

노션에서 아직 특정 기술값이 확정되지 않았으므로 이 문서에서 임의로 고정하지 않는다.
