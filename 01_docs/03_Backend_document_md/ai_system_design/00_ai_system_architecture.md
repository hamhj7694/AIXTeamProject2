# AI 시스템 전체 구조

> 책임: B=lee. 현재 Full/Window Diagnosis·Feature·Risk만 실행 코드가 있으며 Agent·RAG·Voice·Report update는 목표 설계다.

## 1. 목표

여러 자율 Agent를 많이 만드는 것이 목표가 아니다. 서로 독립적인 AI 작업을 일반 Backend가 병렬 실행해 응답시간을 줄이고, AI가 필요한 비정형 판단에만 모델 비용을 사용한다.

## 2. 최종 구성

```text
Frontend
   ↓
일반 Backend Workflow Orchestrator       # 일반 코드
   ├─ Case Intelligence AI               # AI
   ├─ Knowledge & Verification AI        # AI + RAG
   ├─ Case Report AI                     # AI
   └─ Voice Intelligence Pipeline        # STT + AI 분석
   ↓
Schema/Version/Permission 검증            # 일반 코드
   ↓
MySQL 저장 → case_events → Realtime
```

## 3. AI와 일반 코드의 경계

| 기능 | 구현 방식 |
|---|---|
| 호출 순서, 병렬 실행, 재시도, Timeout | 일반 Backend 코드 |
| 인증·권한·DB Transaction·Version | 일반 Backend 코드 |
| P0 표준질문 순서·Recovery 상태 전환 | 규칙 기반 코드 |
| 공식 전화번호·URL 조회 | MySQL 조회 |
| 통화 맥락·위험신호·비정형 답변 해석 | Case Intelligence AI |
| 공식문서 검색·주장 비교·근거 요약 | Knowledge & Verification AI |
| LIVE Section Patch·FINAL Report | Case Report AI |
| STT·화자·Final Segment 분석 | Voice Pipeline |

## 4. 공통 호출 규칙

- Frontend는 일반 Backend만 호출한다.
- AI는 MySQL을 직접 읽거나 수정하지 않는다.
- Backend가 필요한 최소 Case Context만 AI에 전달한다.
- AI는 구조화 JSON, evidence, source ID, version 기준값을 반환한다.
- Backend가 결과를 검증한 뒤 저장·Event 발행한다.
- 동일 Context를 여러 AI에 반복 전달하지 않도록 목적별 Context Projection을 사용한다.

## 5. 병렬 실행 원칙

```text
새 텍스트
  ├─ Full Analysis ─┐
  └─ Window Analysis┤ 병렬
                    ↓
              Feature 조합
               ├─ Risk
               └─ Question Candidate     병렬 가능
                    ↓
              Initial Report
```

- 데이터 의존성이 없는 작업만 병렬 실행한다.
- Report처럼 선행 분석 결과가 필요한 작업은 무조건 뒤에서 실행한다.
- 모든 AI를 매 Event마다 호출하지 않는다.
- Event Impact 규칙으로 필요한 AI와 Section만 호출한다.

## 6. 공통 AI 응답 Envelope

```json
{
  "case_id": "VP-014",
  "request_id": "req_...",
  "model": "provider/model",
  "model_version": "...",
  "schema_version": "1.0",
  "result": {},
  "evidence": [],
  "warnings": [],
  "processing_ms": 0
}
```

## 7. 공통 안전 원칙

- AI가 사기 확정, 법적 확정, 최종 금융조치를 독단적으로 결정하지 않는다.
- 비밀번호, OTP, 보안카드 전체번호, 인증코드를 요청하지 않는다.
- 공식 연락처와 URL을 기억이나 생성으로 반환하지 않는다.
- 근거가 부족하면 `UNKNOWN` 또는 `NEEDS_VERIFICATION`을 반환한다.
- Model/Prompt Version과 사용 근거를 추적한다.

## 8. MVP 우선순위

1. Backend Workflow + Case Intelligence
2. Case Report LIVE Initialize/Update
3. Knowledge Verification RAG
4. FINAL Report
5. Voice Pipeline

Voice와 고급 RAG는 앞 단계 Contract가 안정된 후 연결한다.
