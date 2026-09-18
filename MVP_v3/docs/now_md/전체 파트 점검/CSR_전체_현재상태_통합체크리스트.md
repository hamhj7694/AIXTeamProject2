# CSR 전체 현재상태 통합 체크리스트

최종 갱신: 2026-09-18  
범위: A·B·C 파트 구분 없이, CSR의 AI 분석·채팅·질문·Fact·우측 사건 맥락 패널·고객 공유 흐름 전체

> 이 문서는 현재 구현 상태와 다음 개발 순서를 한 곳에서 확인하기 위한 기준 문서다.  
> 문서에 `[x]`가 있어도 실제 코드·테스트 결과가 없는 항목은 완료로 간주하지 않는다.

## 1. 상태 표기

| 표기 | 의미 |
|---|---|
| `[x]` | 코드와 실행 결과로 확인된 완료 |
| `[~]` | 일부 구현 또는 단위 테스트만 확인됨. 통합 검증이 남음 |
| `[ ]` | 아직 구현·검증하지 않음 |
| `[!]` | 현재 동작에 위험 또는 회귀 가능성이 있음 |
| `HUMAN` | 사람이 의미·정책·승인 결정을 해야 함 |

## 2. 이번 통합의 최종 목표

### 핵심 원칙

- 모든 우측 패널 섹션은 A·B·C별 별도 문장 생성 경로를 사용하지 않는다.
- 채팅, 직원 입력, 고객 답변, 질문 결과, 확정·수정·기각 이벤트를 하나의 최신 사건 맥락으로 합친다.
- LLM이 전체 맥락과 근거를 읽고 패널에 표시할 **완성된 한국어 문장 전체**를 생성한다.
- `기관명`, `행위`, `금액`, `상태` 같은 조각을 코드가 이어 붙여 표시 문장을 만들지 않는다.
- 동일 의미·동일 사건의 반복 정보는 LLM이 통합하고, 서로 다른 실제 이체·사건은 분리한다.
- 새 이벤트가 반영될 때마다 최신 revision 기준으로 패널 문장을 다시 만든다.
- 프론트엔드는 LLM이 만든 표시 문장을 그대로 사용한다. 영어 enum, 내부 변수명, `UNKNOWN`, `OTHER`는 화면에 노출하지 않는다.
- 확정·제안·기각 같은 상태와 버튼은 UI 메타데이터로 표시할 수 있지만, 사실 설명 문장은 LLM 문장이어야 한다.

### 사람이 최종적으로 확인할 수 있어야 하는 질문

1. 이 문장은 현재까지의 최신 대화와 답변을 반영했는가?
2. 원문에 없는 기관·역할·금액·완료 사실을 만들어내지 않았는가?
3. 같은 내용을 중복 표시하지 않았는가?
4. `요청/지시/완료`, `긍정/부정/불명/조건부` 의미가 뒤집히지 않았는가?
5. 근거를 열어보면 실제 메시지·답변·공식 확인과 연결되는가?

## 3. 현재 상태 요약

### 3.1 확인된 구현

- [x] 프론트엔드는 General API를 통해 Case·Message·Context API를 사용한다.
- [x] 초기 Case 분석 결과에 Diagnosis, Semantic Atom, Relation, Signal, Context Feature가 포함된다.
- [x] 초기·일반 채팅·고객 답변의 Context Fact 추출은 provider-backed 경로를 사용하도록 연결되어 있다.
- [x] AI가 만든 Fact 제안은 자동 확정되지 않고 `PROPOSED`로 저장된다.
- [x] Fact에는 근거 메시지·질문 답변·Atom/Signal 연결 정보가 저장된다.
- [x] 같은 금액을 반복해서 확인한 경우와 실제로 다른 이체 사건을 구분하기 위한 lineage/dedupe 로직이 있다.
- [x] Fact 상태는 `PROPOSED`, `CONFIRMED`, `REJECTED`, `SUPERSEDED`로 관리된다.
- [x] 고객용 projection에서 은행 내부 Fact·AI 내부 메시지가 노출되지 않도록 분리되어 있다.
- [x] OpenAI provider의 Context Fact 추출 smoke 호출이 성공하고, 응답에 실제 model 정보가 포함된다.
- [x] `POLICE_SERVICE` 등 내부 enum을 화면에서 한국어로 바꾸는 방어 로직이 있다.
- [x] 초기 Fact·채팅 Fact의 일부 중복을 제거하는 패널 투영 로직이 있다.
- [x] AI extraction, Context Panel, chat/context vertical slice 관련 단위 테스트가 존재하고 통과한 범위가 있다.

### 3.2 아직 목표를 완전히 충족하지 못한 부분

- [!] 우측 패널 전체가 아직 LLM 문장만 사용하는 구조는 아니다.
- [~] 초기·채팅·답변 Fact의 후보 문장은 LLM에서 오지만, 일부 짧은 값은 읽기 좋은 문장을 위해 deterministic fallback이 적용된다.
- [~] `현재 사건 요약`은 구조화 데이터와 기존 저장 문장을 조합하는 경로가 남아 있다.
- [~] 섹션 제목·상태·근거 라벨·업무/공유 항목은 코드 기반 projection이 섞여 있다.
- [!] 확정·수정·기각 후 사건 전체를 LLM에 다시 보내 최신 패널 문장을 재생성하는 공통 경로가 없다.
- [!] 기존 DB에 저장된 legacy Fact 문장이 새 표시 문장으로 일괄 재생성되었다고 볼 수 없다.
- [~] 패널 중복 제거는 현재 일부 deterministic key/점수 규칙에 의존한다. LLM 통합 결과와 함께 검증해야 한다.
- [ ] provider 장애 시 ‘이전 문장 유지/갱신 대기/재시도’ 상태를 사람이 알아보기 쉽게 표시하는 정책이 확정되지 않았다.
- [ ] A·B·C 각각의 패널 섹션이 동일한 `panel_projection` revision을 읽는 통합 E2E가 완료되지 않았다.

### 3.3 현재 주요 코드 경로

| 영역 | 현재 경로 | 역할 |
|---|---|---|
| AI 추출 | `MVP_v3/backend/ai_api/app/domains/case_support/context_fact_extraction_service.py` | provider 호출, 구조화 Fact 후보 생성 |
| 초기/채팅 저장 | `MVP_v3/backend/general_api/app/main.py` | 초기 Case·메시지·답변 후 Fact 저장 |
| 패널 조립 | `MVP_v3/backend/general_api/app/domains/cases/context_v3/panel.py` | 현재 우측 패널 projection 조립 |
| 공개 계약 | `MVP_v3/backend/contracts/public_api/case_context_v2.py` | 패널 응답 모델 |
| 패널 API | `MVP_v3/backend/general_api/app/main.py`의 `/api/cases/{case_id}/context-v2/panel` | 은행/고객 패널 반환 |
| 프론트 패널 | `MVP_v3/frontend/src/context-v3/ContextPanelV3.tsx`, `sections.tsx`, `components.tsx` | 섹션·Fact·상태·근거 표시 |
| 프론트 API | `MVP_v3/frontend/src/context-v3/api.ts` | 패널 조회·Fact review 호출 |

## 4. 통합 목표 데이터 계약

최종적으로 우측 패널은 원천 Fact를 직접 문장화하지 않고, 최신 사건 상태에서 생성된 `panel_projection`을 읽는다.

```json
{
  "case_id": "VP-22",
  "projection_revision": 12,
  "generated_by": "LLM_PROVIDER",
  "model": "gpt-4o-mini",
  "prompt_version": "panel-projection-v1",
  "status": "READY",
  "summary": {
    "display_text": "상대방은 경찰을 사칭해 인증정보 제공과 긴급 이체를 요구했고, 고객은 실제로 300만 원을 이체했다고 진술했습니다.",
    "evidence_refs": ["message-123", "answer-44"]
  },
  "sections": [
    {
      "section_id": "IMPERSONATION_CONTACT",
      "items": [
        {
          "item_id": "projection-item-1",
          "display_text": "상대방은 경찰을 사칭해 고객에게 접근했습니다.",
          "status": "CONFIRMED",
          "evidence_refs": ["message-123"],
          "source_fact_ids": ["fact-9"],
          "display_order": 1
        }
      ]
    }
  ]
}
```

### 계약 규칙

- `display_text`는 LLM이 한 번에 생성한 자연스러운 한국어 완성 문장이다.
- 문장 안에 내부 enum, JSON 키, 영어 변수명, 근거 ID를 넣지 않는다.
- `source_fact_ids`와 `evidence_refs`는 추적용 메타데이터이며 화면 문장에 직접 노출하지 않는다.
- `status`는 문장의 사실 여부가 아니라 검토 상태를 나타낸다.
- `projection_revision`은 Case/Fact/질문 답변/업무 이벤트 변경 revision보다 낮을 수 없다.
- provider 실패 시 코드 문장으로 대체하지 않고 `STALE` 또는 `UPDATE_PENDING` 상태를 반환한다.

## 5. 단계별 개발 계획

### Phase 0 — 기준 동결 및 사람 승인

담당: Codex 준비, `HUMAN` 승인 필요  
목표: 개발 전에 화면 문장과 안전 기준을 고정한다.

- [ ] `panel_projection-v1` 출력 JSON Schema 승인 — `HUMAN`
- [ ] 7개 우측 패널 섹션별 표시 목적과 표시/비표시 범위 승인 — `HUMAN`
- [ ] 한 Fact가 한 문장인지, 여러 독립 사건은 몇 문장까지 허용할지 승인 — `HUMAN`
- [ ] 중복 통합 기준 승인: 동일 의미 반복은 통합, 다른 실제 이체는 분리 — `HUMAN`
- [ ] provider 실패 시 화면 정책 승인: `업데이트 대기` 표시와 재시도 — `HUMAN`
- [ ] Critical contradiction, unsupported concrete value, privacy leak hard gate 승인 — `HUMAN`

완료 조건: 사람이 예시 3건을 보고 “표시 문장으로 채택할 수 있다”고 승인한다.

### Phase 1 — 공통 LLM Panel Projection API

담당: Codex  
목표: A·B·C를 가리지 않고 사건 전체를 한 번에 읽는 provider 경로를 만든다.

- [ ] `PanelProjectionInput` 계약 작성
- [ ] 최신 Case, Fact, Atom/Relation/Signal, 메시지, 질문·답변, 업무 이벤트를 privacy-safe snapshot으로 구성
- [ ] 확정·제안·기각·대체 상태를 LLM 입력에 명시
- [ ] 근거가 없는 항목은 생성하지 않도록 prompt 작성
- [ ] 각 항목의 `display_text`를 완성 문장으로 요구
- [ ] 동일 의미 반복, 동일 금액 재언급, 실제 별도 이체를 구분하도록 prompt와 schema 작성
- [ ] 출력 schema 검증 및 허용 목록 밖 항목 제거
- [ ] `model`, `prompt_version`, `usage`, `latency`, `source_revision` 저장
- [ ] provider-only 원칙: deterministic 문장 생성으로 대체하지 않음

완료 조건: 같은 snapshot에 대해 provider 응답으로 7개 섹션을 구성하고, 표시 문장에 코드 조각이 없다.

### Phase 2 — 서버 저장·revision·재생성 트리거

담당: Codex  
목표: 새로고침 후에도 최신 LLM 결과를 복원하고, 모든 변경 뒤에 재생성한다.

- [ ] `panel_projections` 또는 동등한 durable 저장 구조 추가
- [ ] Case 생성 후 최초 projection 생성
- [ ] 일반 채팅 저장 후 projection 재생성
- [ ] 직원 내부 채팅 저장 후 projection 재생성
- [ ] 고객 질문 답변 저장 후 projection 재생성
- [ ] Fact 확정·기각·수정·복구 후 projection 재생성
- [ ] 업무 추가·완료·취소 및 고객 공유 변경 후 projection 재생성
- [ ] 동일 revision 중복 호출 방지용 idempotency key 추가
- [ ] 오래된 provider 응답이 최신 projection을 덮어쓰지 못하도록 revision 검증
- [ ] provider timeout/실패 시 `UPDATE_PENDING`과 재시도 상태 저장
- [ ] 최신 성공 projection과 현재 revision이 다르면 패널에 stale 상태 표시

완료 조건: 새로고침·재접속 후 같은 projection이 보이고, 이전 revision 응답이 최신 상태를 덮어쓰지 않는다.

### Phase 3 — 7개 우측 패널 섹션 통합

담당: Codex  
대상: `SUMMARY`, `EXPOSURE`, `IMPERSONATION_CONTACT`, `FRAUD_CIRCUMSTANCES`, `FACT_VERIFICATION`, `STAFF_ACTIONS`, `CUSTOMER_SHARE`

- [ ] `panel.py`의 사용자 표시 문장 조립 경로를 projection 읽기 경로로 변경
- [ ] `현재 사건 요약`을 별도 deterministic 문장 조합 없이 projection의 `summary.display_text`로 표시
- [ ] 피해·노출, 사칭·접촉, 사기 정황의 Fact 문장을 projection 문장으로 표시
- [ ] 사실·확인 현황은 제안/확정/기각 상태와 LLM 문장을 함께 표시
- [ ] 직원 조치·결과는 업무 상태 메타데이터와 LLM 결과 문장을 분리 표시
- [ ] 고객 공유는 고객 공개용 projection만 표시하고 내부 근거는 제거
- [ ] 섹션 제목·버튼·상태 배지는 고정 UI 문구로 유지하되 사실 설명은 LLM 문장 사용
- [ ] 영어 변수명·`AI 추출`·`UNKNOWN`·`OTHER` 직접 노출 제거
- [ ] 동일 의미의 legacy Fact 문장은 projection에서 하나로 통합
- [ ] 서로 다른 실제 이체·요구·답변은 source lineage 기준으로 별도 표시

완료 조건: 7개 섹션 어느 곳에서도 사용자 표시용 deterministic 문장 조립이 사용되지 않는다.

### Phase 4 — 프론트엔드 표시 경로 정리

담당: Codex  
목표: 프론트는 LLM 결과를 조립하지 않고 표시만 한다.

- [ ] `ContextPanelV3`가 `panel_projection` 응답을 단일 데이터 원본으로 사용
- [ ] `staffDisplayValue`의 enum 문장 조립 fallback 제거 또는 내부 진단 전용으로 제한
- [ ] 문장·상태·근거·원천 Fact를 서로 다른 UI 영역으로 구분
- [ ] 긴 LLM 문장 줄바꿈과 카드 폭 고정
- [ ] `READY`, `UPDATE_PENDING`, `STALE`, `FAILED` 표시 상태 추가
- [ ] provider 실패 시 이전 문장을 새 사실처럼 표시하지 않도록 시각적 경고
- [ ] 은행 화면과 고객 화면의 projection/visibility 분리 유지
- [ ] 패널 갱신 시 중앙 채팅 revision과 불일치하면 재조회

완료 조건: 브라우저에서 표시되는 사실 설명은 API의 `display_text`와 문자 단위로 일치한다.

### Phase 5 — 기존 데이터 정리 및 migration

담당: Codex 실행, 운영 정책은 `HUMAN` 승인

- [ ] legacy Fact별 원천 근거와 현재 상태 점검
- [ ] 원문 근거가 없는 Fact는 projection 입력에서 제외하거나 `검토 필요`로 격리
- [ ] 기존 deterministic 표시 문장을 새 LLM projection으로 재생성
- [ ] 동일 의미 중복 Fact는 원천 ID를 보존한 채 표시 항목을 통합
- [ ] 실제 별도 금액 사건은 합산하지 않고 lineage별로 유지
- [ ] migration 전후 item 수·근거 수·상태 변화 보고서 생성
- [ ] migration 결과를 사람에게 승인받은 뒤 운영 화면에 반영 — `HUMAN`

완료 조건: 기존 화면에 남아 있던 영어 변수명·generic 문장·중복 표시가 새로고침 후 재등장하지 않는다.

### Phase 6 — 테스트·품질 측정

담당: Codex 실행, 대표 사례 판정은 `HUMAN`

#### 자동 테스트

- [ ] provider 응답 schema 검증
- [ ] display_text 완성 문장 검증
- [ ] 영어 enum/내부 키 노출 검출
- [ ] 근거 없는 기관·역할·금액 생성 검출
- [ ] 동일 메시지 반복 입력 idempotency
- [ ] 다른 실제 이체 lineage 보존
- [ ] revision 순서 역전 방지
- [ ] projection 저장·복원·재시도
- [ ] 은행/고객 visibility 분리
- [ ] 7개 섹션 projection 정확성
- [ ] TypeScript 검사, backend compileall, API 통합 테스트

#### 공식 fixture 평가

- [ ] Context Feature Recall / Precision / F1
- [ ] Critical Fact Recall / Precision
- [ ] Status·Polarity·Modality·Action-state 보존
- [ ] Relation accuracy
- [ ] Correction resolution accuracy
- [ ] Fact lineage completeness
- [ ] Section projection accuracy
- [ ] Critical contradiction rate
- [ ] Critical hallucination/unsupported claim rate
- [ ] Privacy leak rate
- [ ] Pipeline completion rate
- [ ] Token, call count, latency P50/P95/MAX
- [ ] Token per correct critical fact

#### 사람 검토

- [ ] FACT-01~03의 실제 의미 보존 검토 — `HUMAN`
- [ ] 대표 critical case의 자연스러움 검토 — `HUMAN`
- [ ] 각 case를 `APPROVED / NEEDS_CORRECTION / REJECTED`로 결정 — `HUMAN`
- [ ] 금액·부정·조건부·요청/완료 의미가 바뀌지 않았는지 확인 — `HUMAN`
- [ ] 고객에게 노출되어도 안전한 문장인지 확인 — `HUMAN`

### Phase 7 — 운영 전환

- [ ] staging에서 3회 반복 실행하여 평균·분산 확인
- [ ] provider 비용·호출 수·latency 상한 확인
- [ ] 실패/재시도/부분 성공 모니터링 추가
- [ ] 운영 로그에 prompt 원문·민감정보·API key가 남지 않는지 확인
- [ ] feature flag로 구 projection과 신 projection을 비교할 수 있게 구성
- [ ] 사람 승인 후 신 projection 기본 사용 전환 — `HUMAN`
- [ ] 기존 projection 제거 시점과 복구 방법 결정 — `HUMAN`

## 6. 사람이 해야 하는 일

개발자가 대신 결정하면 안 되는 항목은 다음과 같다.

- [ ] 예시 문장이 원문 의미를 정확히 보존하는지 승인
- [ ] 동일 의미 반복과 별도 사건을 구분하는 정책 승인
- [ ] `확정`, `검토 필요`, `기각`의 업무상 의미 승인
- [ ] 고객 공개 가능 문장 승인
- [ ] provider 장애 시 이전 문장을 보여줄지, 갱신 대기로 표시할지 승인
- [ ] migration 결과에서 합쳐진 항목과 제외된 항목 승인
- [ ] 공식 benchmark의 모델·환경·fixture·hard gate 승인

사람이 입력해야 하는 값은 Fact 문장을 직접 작성하는 것이 아니라, **LLM이 만든 문장이 사실과 맞는지 결정하는 것**이다.

## 7. Codex가 해야 하는 일

- [ ] 공통 `panel_projection` schema와 provider prompt 구현
- [ ] 최신 전체 사건 snapshot 구성
- [ ] 모든 이벤트 후 projection 재생성 트리거 연결
- [ ] projection 저장·revision·idempotency·retry 구현
- [ ] 7개 우측 패널을 projection 단일 경로로 전환
- [ ] 영어 enum/코드 조립 문장 제거
- [ ] legacy projection migration 도구 작성
- [ ] API·프론트·DB 통합 테스트 작성 및 실행
- [ ] benchmark 결과와 사람이 읽는 보고서 생성
- [ ] 실패 상태와 stale 상태를 UI에 표시

## 8. 완료 판정 기준

다음 항목을 모두 만족하기 전에는 “우측 패널 전체가 LLM 기반으로 완료됐다”고 표시하지 않는다.

- [ ] 7개 섹션의 사실 설명이 모두 provider `display_text`에서 나온다.
- [ ] 새 채팅·답변·확정·수정·기각 후 최신 revision projection이 생성된다.
- [ ] 새로고침 후에도 같은 projection이 복원된다.
- [ ] 동일 내용은 중복되지 않고, 다른 실제 사건은 합쳐지지 않는다.
- [ ] 영어 변수명·enum·코드 조합 문장이 화면에 없다.
- [ ] 근거 없는 구체값·완료 승격·critical contradiction이 0건이다.
- [ ] 고객 화면에 은행 내부 정보가 노출되지 않는다.
- [ ] provider 실패 시 deterministic 문장으로 위장하지 않고 갱신 대기 상태를 표시한다.
- [ ] 자동 테스트와 공식 replay 결과가 기록되어 있다.
- [ ] 대표 결과를 사람이 승인했다.

## 9. 현재 실행·검증 명령

```powershell
cd C:\Users\mbc\Documents\GitHub\AIXTeamProject2\MVP_v3\backend
..\.venv\Scripts\python.exe -m uvicorn ai_api.app.main:app --host 127.0.0.1 --port 8101 --reload
```

```powershell
cd C:\Users\mbc\Documents\GitHub\AIXTeamProject2\MVP_v3\backend
..\.venv\Scripts\python.exe -m uvicorn general_api.app.main:app --host 127.0.0.1 --port 8100 --reload
```

```powershell
Invoke-RestMethod http://127.0.0.1:8101/readiness
Invoke-RestMethod http://127.0.0.1:8100/health
```

권장 검증 순서:

1. AI readiness에서 `provider_configured=true`, `context_fact_extraction=provider_only` 확인
2. provider smoke 1건 실행
3. Case 생성 → 채팅 → 질문 답변 → Fact 확정/수정/기각 순서로 projection revision 확인
4. 브라우저 강력 새로고침 후 패널 문장·상태·근거 복원 확인
5. 자동 테스트와 공식 replay 결과를 보고서에 기록

## 10. 관련 문서·코드 정리 원칙

- 이 문서를 전체 진행 기준으로 사용한다.
- A파트의 세부 benchmark 문서는 평가 fixture·측정 방법을 설명하는 보조 문서로만 사용한다.
- `A_IMPLEMENTATION_CHECKLIST.md`는 A파트 내부 구현 세부사항을 기록하고, 전체 완료 판정은 이 문서와 맞춘다.
- `official_comparison_report.md`는 실제 replay 수치만 기록하며, 구현 완료를 추정해서 표시하지 않는다.
- 새 문서를 만들 때 동일 체크리스트를 복제하지 말고 이 문서에 링크와 상태를 추가한다.

## 11. 현재 결론

현재 CSR은 **LLM 기반 Fact 후보 생성과 일부 패널 표시까지 구현된 상태**다. 그러나 사용자가 요구한 “A·B·C 구분 없이 우측 패널의 모든 설명 문장을 최신 전체 사건을 읽은 LLM이 통째로 생성”하는 최종 구조는 아직 완료되지 않았다.

다음 개발의 첫 단계는 Phase 0의 사람 승인 후 Phase 1의 공통 `panel_projection` 계약을 만드는 것이다. 그 계약과 revision 저장 경로가 완성되기 전에는 개별 섹션만 임시로 고치는 방식으로 완료 처리하지 않는다.

## 12. 프론트엔드 우선 재설계 작업공간

새 프론트엔드 설계·View Model 초안·작업 체크리스트는 다음 폴더에서만 관리한다.

- [`FRONTEND_REBUILD_20260918`](../FRONTEND_REBUILD_20260918/README.md)

현재 foundation 단계에서는 좌측·중앙·우측 큰 틀만 보존하고, 중앙의 legacy 카드와 우측 패널의 데이터 표시를 비운다. 기존 API·백엔드 계약은 참고용으로 보존하며, 새 View Model이 사람 승인되기 전에는 기존 계약을 새 화면에 맞춰 임의 수정하지 않는다.
