# B Part 현재 진행 상태

이 문서는 현재 작업 상태만 기록하며 자주 갱신한다.

기존 checklist는 사용하지 않는다.

## Baseline

```text
Branch:
feat/b-dynamic-question-plan-p3

HEAD:
39c7732
```

문서 작업 시작 시 확인한 결과:

```text
?? MVP_v3/docs/now_md/B_part/
```

시작 시 추적 중인 코드 파일 변경은 없었다. 이번 작업의 공식 문서 4개 생성과 checklist 이동은 문서 변경이다. 폴더 전체가 추적되지 않아 작업 후에도 같은 폴더 단위로 표시된다.

아래 완료 단계, 테스트 수치와 P3-4 READ-ONLY 분석 결과는 이번 요청에서 제공된 확정 기록이다. 이번 문서 작업에서는 테스트와 구현 분석을 재실행하지 않았다.

## 완료 단계

```text
P0 Customer Answer Structure          완료
P1 Question Recommendation 기반       완료
P2 Copilot Quality / Grounding 기반   완료
P3-1 Semantic State Foundation        완료
P3-2 Question Eligibility             완료
P3-3 Dynamic Question Plan            완료
```

### P3-2

commit:

```text
1644952
feat(question-eligibility): integrate semantic question eligibility
```

targeted validation:

```text
66 tests passed
44 subtests passed
0 failures
```

### P3-3

commit:

```text
39c7732
feat(question-plan): add dynamic follow-up question flow
```

targeted validation:

```text
AI:
60 passed
60 subtests passed

General:
37 passed
19 subtests passed
6 deprecation warnings

Total:
97 tests passed
79 subtests passed
0 failures
```

Deprecation warning은 기능 실패와 구분한다.

## 현재 단계

```text
P3-4 Source-aware Bank Copilot
```

P3-4 READ-ONLY 분석 완료.

판정:

```text
SOURCE_CONTRACT_EXTENSION_REQUIRED
READY_FOR_P3_4_IMPLEMENTATION
```

핵심 원인:

```text
Case Context / V2 Fact에는 provenance 정보가 존재하지만
Bank Copilot으로 전달되는 과정에서 list[str] 중심으로 축약되어
source / evidence / freshness / supersede 의미가 손실됨.
```

현재 확인된 주요 손실 경계:

* `general_api/app/domains/cases/case_retrieval.py`
* `general_api/app/main.py`
* `contracts/ai_internal/case_copilot.py`
* `ai_api/app/domains/case_support/copilot_service.py`

P3-4 목표:

* typed source/provenance 보존
* customer statement와 bank record 구분
* completed Verification을 claim 범위에 맞게 사용
* 최신/current/superseded 정보 보존
* 현재 질문에 직접 답변
* unsupported certainty 검사 강화
* 실제 전달되지 않은 Evidence를 확인된 사실처럼 표현하지 않기

DB migration은 현재 필요하지 않다.

## 다음 단계

```text
P3-4 Source-aware Bank Copilot 구현
→ targeted validation
→ commit

P3-5 Regression / REST E2E
→ 전체 Case Workflow 통합 검증
```

P3-5에서는 다음 흐름을 최종 검증한다.

```text
Case
→ 질문 추천
→ 담당자 검토
→ 고객 전송
→ 고객 답변
→ Fact / Semantic State 갱신
→ 다음 질문
→ Bank Copilot
```

## 남은 Integration Requirement

현재 명확히 남은 항목:

* typed conflict/correction relation의 production 연결
* Bank Copilot typed provenance 전달
* 실제 거래 원본 Evidence가 전달되지 않은 경우 안전한 표현
* P3-5 MySQL / REST / Browser / Live AI 검증

공식기관 Verification / RAG / Vector DB는 핵심 Workflow 안정화 이후 필요성을 재검토한다.
