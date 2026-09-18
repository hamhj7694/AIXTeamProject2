# B Part 기본 원칙

이 문서는 거의 변하지 않는 B Part의 기본 원칙을 정의한다.

## 1. B Part 역할

B Part는 Assisted Conversation & Verification 영역을 담당한다.

핵심 Workflow:

```text
Case Context
→ 확인이 필요한 정보 판단
→ 질문 추천
→ 담당자 검토
→ 고객 전달
→ 고객 답변
→ 답변 구조화
→ Case Context 반영
→ 다음 질문 갱신
→ 필요한 경우 Verification 연결
```

AI는 최종 판단자가 아니다.

AI 역할:

* 사건 정보 구조화
* 부족한 정보 식별
* 확인 질문 추천
* 답변 맥락 정리
* 근거 수준을 구분한 설명
* 담당자 판단 지원

AI가 자동으로 수행하지 않는 것:

* 질문 자동 전송
* 사건 자동 종료
* 지급정지 등 강한 금융 조치
* 고객 진술의 자동 사실 확정

## 2. 의미 규칙

다음은 고정 원칙이다.

```text
ANSWERED != SUFFICIENT

PROPOSED != CONFIRMED

CUSTOMER_STATEMENT != VERIFIED FACT

CUSTOMER_REPORTED_COMPLETED != VERIFIED_COMPLETED

UNKNOWN != FALSE
```

고객이 말했다는 사실과 실제 사건 사실이 확인됐다는 것은 구분한다.

예:

```text
"고객은 1,000만원을 송금했다고 진술했습니다."
```

와

```text
"은행 거래기록에서 1,000만원 이체가 확인됩니다."
```

는 서로 다른 근거 수준이다.

## 3. Source와 Status

`source`와 `status`는 서로 다른 개념이다.

예:

```text
source = CUSTOMER_STATEMENT
status = CONFIRMED
```

일 수 있다.

`CONFIRMED`라는 이유만으로 `BANK_RECORD`로 해석하지 않는다.

또한 Evidence reference가 존재하는 것과 원본 Evidence 내용을 실제로 검증한 것도 구분한다.

## 4. 개발 원칙

```text
READ-ONLY 분석
→ 변경 설계
→ 최소 구현
→ targeted test
→ Workflow 검증
```

우선순위:

```text
Evidence > 추측
기존 코드 보존 > 재작성
최소 수정 > 대규모 변경
완성 가능한 Workflow > 기능 개수
문제 해결 > 기술 추가
```

RAG, Vector DB, Agent 등은 실제 문제가 확인될 때만 추가한다.

### Frontend 작업 경계

현재 frontend는 별도 담당자가 수정 중이므로 B Part 작업에서는 기본적으로 수정하지 않는다.

* frontend 파일은 필요 시 READ-ONLY 확인만 허용한다.
* frontend 변경 필요성이 발견되면 직접 수정하지 않고 `FRONTEND_INTEGRATION_REQUIREMENT`로 기록한다.
* backend/API contract 변경 시 기존 frontend 호환성을 우선 확인한다.
* P3-5 Browser/UI 검증에서 문제가 발견되더라도 backend/API 문제인지 frontend 문제인지 먼저 분리한다.
* frontend 문제로 판단되면 B Part에서 임의 수정하지 않고 별도 담당자 작업 항목으로 전달한다.

## 5. 문서 검토 깊이 원칙

문서의 중요도에 따라 검토 깊이를 구분한다.

* 기준 문서 / Contract / 설계 문서:
  전체 내용을 정독하고 충돌, 중복, 누락, 오래된 규칙까지 검토한다.
  중요 변경이 발생한 경우 변경 부분만 보지 않고 전체 기준과의 일관성을 다시 확인한다.

* 진행 상태 문서:
  branch/HEAD, 완료 단계, 테스트 결과, 현재 작업, 남은 blocker 중심으로 확인한다.

* 코드 작업 결과 / 로그:
  전체를 기계적으로 검토하기보다 변경된 영역, 영향 범위, 공용 Contract/API/Repository 경계를 우선 확인한다.

* drafts / 과거 문서:
  별도 필요가 있을 때만 확인하며 현재 구현 판단의 기본 근거로 사용하지 않는다.

검토 깊이는 정확성과 작업 효율성을 함께 고려해 결정한다.

## 6. Codex 작업 규칙

* Codex 프롬프트는 현재 작업에 직접 필요한 내용만 포함한다.
* 기준 문서 전체를 매번 프롬프트에 반복하지 않는다.
* 동일 기능과 파일을 이어서 작업하면 기존 Codex 대화를 우선 사용한다.
* READ-ONLY 작업 중 발견한 개선사항은 별도 지시 없이 구현하지 않는다.
* 확인되지 않은 구현이나 테스트를 완료로 표시하지 않는다.

## 7. Codex 완료 보고 언어

**Codex 완료 보고는 반드시 자연스러운 한국어로 작성한다.**

다음은 원문을 유지한다.

* 코드 식별자
* enum
* 함수명
* 클래스명
* 파일 경로
* Git 명령어
* 테스트 명령어
* 상태 코드명

예:

```text
READY_FOR_P3_4_IMPLEMENTATION
```

같은 상태명은 그대로 사용하고 설명은 한국어로 작성한다.
