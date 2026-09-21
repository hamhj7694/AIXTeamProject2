# B Part — 질문 추천·확인 사실·대화 UX 개선 체크리스트

작성일: 2026-09-21
상태: IN_PROGRESS

---

## 1. 문서 목적

이 문서는 `B_QUESTION_AND_CONFIRMATION_IMPROVEMENT_PLAN.md`의 진행 상태를 관리하기 위한 체크리스트입니다.

세부 구현 항목을 하나씩 나열하기보다, 각 작업을 기능 단위로 묶어 완료 여부를 확인합니다.

### 공통 진행 방식

각 작업은 아래 흐름을 기본으로 진행합니다.

```text
READ-ONLY 구조 확인
→ 변경 방향 확정
→ 최소 구현
→ 자동 테스트
→ Runtime / Browser 검증
→ 문서 갱신
```

### 공통 제약

- 기존 MVP_v3의 DB 테이블·컬럼·관계 구조를 변경하지 않습니다.
- 새로운 요구사항은 기존 DB 구조와 Contract를 우선 재사용합니다.
- 기존 구조만으로 구현이 불가능한 경우 임의로 migration이나 schema 변경을 진행하지 않고, 원인과 필요한 변경을 별도로 보고합니다.
- 담당자 승인 전 고객에게 질문을 자동 전송하지 않습니다.
- 기존 B Part의 질문 lifecycle, batching, supersede, qf1, Quality/Grounding 안전 경계를 유지합니다.

---

# 0. CSR 질문 매뉴얼 작성

### 목표

추천 질문 생성의 기준이 되는 Target, 단계, 우선순위, 질문 조건, 생략 조건, 충분한 답변 기준 등을 정의합니다.

- [x] 질문 매뉴얼 초안 작성
- [x] 단계·Target·우선순위 검토
- [x] `ask_when / skip_when / sufficient_answer / follow-up` 기준 검토
- [x] 실제 보이스피싱 대응 근거와 프로젝트 데이터 반영 여부 검토
- [ ] 매뉴얼 확정

### 완료 조건

- 질문 문장 목록이 아니라 `확인해야 할 Target` 중심으로 정리되어 있음
- 이미 충분히 확인된 Target을 재질문하지 않는 기준이 포함되어 있음
- 이후 추천 질문 생성에서 실제로 사용할 수 있는 구조로 정리되어 있음

상태: `IN_PROGRESS` — 최종 사용자 검토와 매뉴얼 확정이 남아 있음

---

# 1. 매뉴얼 + Case Context 기반 추천 질문 생성

### 목표

질문 매뉴얼과 Case 데이터를 함께 사용해 이미 확인된 내용은 제외하고 현재 필요한 질문만 추천하도록 개선합니다.

- [x] READ-ONLY 구조 확인
- [x] 변경 방향 확정
- [x] 구현 완료
- [ ] 자동 테스트 통과
- [ ] Runtime / Browser 검증
- [ ] 관련 문서 갱신

### 완료 조건

- 이미 충분히 확인된 Target 재질문 없음
- 기존 `PENDING / ASKED` 질문은 중복 추천하지 않음
- `ANSWERED` 질문은 답변 충분성을 별도로 평가
- `ANSWERED`이지만 `UNCERTAIN`이면 동일 기본 질문을 반복하지 않고 `qf1` 등 기존 후속 확인 흐름을 사용
- `ANSWERED != SUFFICIENT` 원칙 유지
- 의미만 다른 동일 canonical target 질문 중복 없음
- `claimed_organization` / `impersonated_institution`의 conceptual duplicate 검토, 코드 alias 변경 없음
- 현재 단계에 필요한 질문을 우선 추천
- 유효 후보 전체 수에 임의의 고정 상한이 없음
- 담당자 화면은 기본 5개를 한 묶음으로 표시하며, 5개 초과 유효 후보도 버리지 않고 이후 확인 가능한 추가 후보로 유지
- 필요한 후보가 5개 미만이면 해당 수만 표시하고 묶음 크기를 채우기 위해 불필요한 질문을 생성하지 않음
- `UNMAPPED` 매뉴얼 후보는 1차 자동 추천에 직접 사용하지 않음
- 담당자 검토 전 고객 자동 전송 없음
- 기존 DB 구조 변경 없음

상태: `IN_PROGRESS`

---

# 2. 직원 확인 사실 반영 및 AI 응답 안정화

### 목표

확정 표현을 사용할 수 없는 상황에서도 단순 오류 대신 설명형 AI_RESPONSE를 제공하고, 담당자 확인 사실을 Case Context에 반영할 수 있도록 개선합니다.

- [ ] 현재 Quality / Grounding / Fact 반영 흐름 READ-ONLY 확인
- [ ] 2-1 설명형 AI_RESPONSE 처리 방향 확정 및 구현
- [ ] 2-2 직원 확인 사실의 `CONFIRMED` 반영 흐름 확정 및 구현
- [ ] 2-3 확인 사실 카드 / 직접 입력 흐름 확정 및 구현
- [ ] 자동 테스트 통과
- [ ] Runtime / Browser 검증
- [ ] 관련 문서 갱신

### 완료 조건

- `unsupported_certainty` 등으로 확정 표현이 불가능해도 단순 오류로 끝나지 않음
- 현재 확인 상태, 확정 불가 이유, 다음 확인 방법을 설명하는 안전한 응답 제공
- 직원 확인 사실은 provenance와 함께 관리됨
- `CONFIRMED`와 `VERIFIED`가 구분됨
- `UNKNOWN`을 `FALSE`로 처리하지 않음
- Quality/Grounding 기준을 우회하거나 완화하지 않음
- 기존 DB 구조 변경 없음

상태: `TODO`

---

# 3. 질문 발송·답변 카드 UI 정리

### 목표

여러 질문 발송 기록을 한 묶음으로 표시하고, 고객 답변은 답변 시점의 별도 Q&A 이벤트로 보여주도록 개선합니다.

- [ ] 현재 질문 / 답변 렌더링 흐름 READ-ONLY 확인
- [ ] UI 변경 방향 확정
- [ ] 구현 완료
- [ ] Frontend typecheck / build 통과
- [ ] Browser E2E 검증
- [ ] 관련 문서 갱신

### 완료 조건

- 같은 발송 batch의 질문은 `질문 N건 발송됨` 형태로 한 묶음 표시
- 펼치면 실제 질문 목록 확인 가능
- 내부 질문 lifecycle은 개별 유지
- 고객 답변은 답변 시점의 별도 Q&A 이벤트로 표시
- 질문과 답변은 하나의 카드로 표시
- `고객 답변` 라벨 제거
- Customer ROOM의 한 질문씩 노출 흐름 유지
- 기존 DB 구조 변경 없음

상태: `TODO`

---

# 4. AI 답변 핵심 정리 표현 개선

### 목표

AI 답변 마지막에 현재 상황을 빠르게 파악할 수 있는 핵심 정리 또는 다음 확인 포인트를 제공합니다.

- [ ] 현재 출력 구조 확인 및 표현 형식 확정
- [ ] 구현 완료
- [ ] Runtime / Browser 검증
- [ ] 관련 문서 갱신

### 완료 조건

- 핵심 정리 또는 다음 확인 포인트가 일관되게 표시됨
- AI가 사건의 최종 판단자로 보이지 않음
- 기존 AI 응답 내용과 역할 구분이 유지됨

상태: `TODO`

---

# 5. Bank AI 대화 ↔ 고객 확인 질문 기능 연동

### 목표

Bank AI가 제안한 질문을 기존 `고객에게 확인 질문` 기능으로 가져와 담당자가 검토·수정 후 사용할 수 있도록 연결합니다.

- [ ] Bank AI와 기존 질문 기능 연결 구조 READ-ONLY 확인
- [ ] 기존 추천 질문 로직 재사용 방식 확정
- [ ] 기능 연동 구현
- [ ] Runtime / Browser 검증
- [ ] 관련 문서 갱신

### 완료 조건

- Bank AI 추천 질문을 기존 고객 확인 질문 UI로 가져올 수 있음
- 담당자가 선택·수정 후 전송 가능
- AI 답변에서 고객에게 직접 자동 발송되지 않음
- 별도 추천 엔진을 중복 구현하지 않음
- 기존 DB 구조 변경 없음

상태: `TODO`

---

# 6. AI 답변에서 다음 단계 Action 연결

### 목표

AI 답변 이후 담당자가 현재 상황에 맞는 기존 기능으로 빠르게 이동할 수 있도록 Action을 연결합니다.

- [ ] 연결 가능한 기존 기능과 노출 조건 확인
- [ ] Action 범위 확정 및 구현
- [ ] Runtime / Browser 검증
- [ ] 관련 문서 갱신

### 완료 조건

- 현재 상황에 맞는 기존 기능으로 이동하거나 입력을 준비할 수 있음
- AI가 강한 조치를 자동 실행하지 않음
- 기존 기능을 재사용하며 불필요한 중복 기능 없음

상태: `TODO`

---

# 7. B Part 전체 회귀 검증

모든 개선 작업이 끝난 뒤 기존 B Part 핵심 기능이 유지되는지 확인합니다.

- [ ] Bank 연속 메시지 batching 정상
- [ ] Bank in-flight supersede 정상
- [ ] Customer batching / supersede 정상
- [ ] stale AI_RESPONSE 저장 방지 정상
- [ ] `PENDING → ASKED → ANSWERED` 정상
- [ ] QUESTION / ANSWER 저장 정상
- [ ] Customer answer 반영 정상
- [ ] qf1 parent / target / duplicate 보호 정상
- [ ] 담당자 승인 전 고객 자동 전송 없음
- [ ] Case Context provenance 유지
- [ ] Quality / Grounding 안전 경계 유지
- [ ] 기존 DB 테이블 / 컬럼 / 관계 구조 변경 없음
- [ ] 주요 자동 테스트 PASS
- [ ] 주요 Browser E2E PASS

상태: `TODO`

---

# 8. B Part 최종 완료 조건

아래 조건을 모두 만족하면 B Part를 최종 `DONE`으로 처리합니다.

- [ ] 0 / 1 / 2 / 3 / 4 / 5 / 6 작업 완료
- [ ] 질문 추천 Workflow가 실제 Case 기준으로 정상 동작
- [ ] 담당자 확인 사실이 Case Context에 안전하게 반영됨
- [ ] Quality 차단 상황에서 단순 오류 대신 설명형 응답 제공
- [ ] 질문 발송 / 고객 답변 UI 개선 완료
- [ ] Bank AI와 고객 확인 질문 기능 연동 완료
- [ ] 주요 회귀 테스트 통과
- [ ] Browser에서 B Part 핵심 Workflow를 처음부터 끝까지 확인
- [ ] 남아 있는 P0 수준의 미해결 오류 없음
- [ ] DB schema 변경 없음
- [ ] 작업 계획 / 체크리스트 / 질문 매뉴얼 문서 최신 상태 반영
- [ ] 변경사항 commit / push 완료
- [ ] 필요한 PR / merge 상태 확인

최종 상태: `B PART TODO`
