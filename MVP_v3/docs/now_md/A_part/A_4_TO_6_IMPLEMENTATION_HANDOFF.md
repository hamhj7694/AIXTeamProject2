# A파트 4~6단계 구현 메모

작성일: 2026-09-16

## 목표

`Semantic Atom → Relation/Context Signal → Fact → 직원용 문장`의 단방향 연결을 고정한다.

- 중앙 `analysis-result created`: 구조화 분석 결과를 보존하고 개발자/내부 분석용으로 조회한다.
- 은행 우측 Context Panel: Fact만 입력으로 사용해 기존 7개 섹션의 직원용 문장으로 표시한다.
- Frontend는 현재 freeze를 유지한다. 백엔드는 기존 응답 계약을 깨지 않고 additive field와 기존 Fact API를 사용한다.

## 4단계 — Fact 저장 계약

### 저장 규칙

1. AI가 만든 Fact는 항상 `PROPOSED`로 시작한다.
2. Fact에는 `semantic_key`, `value`, `display_value`, `source_kind`, `evidence_refs`, `confidence`, `version`을 보존한다.
3. `STRUCTURED_ATOM`·`STRUCTURED_SIGNAL` reference에는 실제 Atom/Signal ID만 넣고 원문을 넣지 않는다.
4. 직원 확인만 `CONFIRMED`로 전환할 수 있다.
5. 수정은 기존 Fact를 덮어쓰지 않고 새 revision을 만들며 이전 Fact는 `SUPERSEDED`로 연결한다.
6. 같은 semantic slot에 상충 값이 있으면 자동 병합하지 않고 별도 Fact와 conflict 상태로 남긴다.
7. `client_request_id`와 semantic fingerprint로 retry/idempotency를 보장한다.

### 금지

- 통화 원문, 긴 evidence span, 인증 secret·계좌번호 literal 저장
- AI 결과의 자동 `CONFIRMED` 전환
- 서로 다른 금액·요구·주장을 하나의 broad Fact로 합치기

## 5단계 — 기존 패널 Fact projection

모든 Atom을 화면에 직접 그리지 않고 semantic key별로 기존 섹션에 매핑한다.

| Atom 의미 | 패널 섹션 | Fact 원칙 |
| --- | --- | --- |
| 인증정보 요구 | 피해·노출 | OTP/비밀번호 유형별 개별 Fact |
| 송금·인출·대출 | 피해·노출 | 금액·대상·목적별 개별 Fact |
| 기관·역할 주장 | 사칭·접촉 정보 | 기관과 역할을 별도 Fact |
| 통화 종료·가족·은행 연락 차단 | 사칭·접촉 정보 | `communication_control` 유형별 Fact |
| 긴급성·공포·권위·고립 | 사기 정황 | 압박 수법별 개별 Fact |
| 고객의 실제 행동 | 사실·확인 현황 | `REPORTED_ACTION`와 `VERIFIED` 분리 |

projection deduplication은 `semantic_key + 핵심 value + source_atom_ids` 단위로 수행한다. 금액·대상·목적이 다르면 절대 합치지 않는다.

## 6단계 — Grounded 문장화

1. Fact 하나당 직원용 문장 하나를 만든다.
2. 문장은 supporting Atom/Relation/Fact에 있는 값만 사용한다.
3. `PROPOSED`는 “요구 정황이 확인됨”, `CONFIRMED`는 “확인됨”처럼 상태를 보존한다.
4. `REQUESTED`, `INSTRUCTED`, `REPORTED_ACTION`, `VERIFIED`, `UNKNOWN`, `NEGATIVE`, `CONDITIONAL`을 서로 바꾸지 않는다.
5. `observed_terms`가 있으면 짧은 핵심 용어만 문장에 반영하고, 없으면 표현을 임의로 만들지 않는다.
6. Relation이 없으면 두 Fact를 인과·목적 관계 문장으로 합치지 않는다.
7. 생성 후 validator가 Fact의 semantic key·상태·금액·대상·근거를 다시 검사한다.

## 단계 간 완료 조건

```text
4단계 완료: 저장·확정·수정·충돌·재시도 계약과 persistence test 통과
5단계 완료: 모든 의미 Atom이 기존 패널 Fact로 매핑되고 다중 값이 보존됨
6단계 완료: 모든 Fact가 상태·근거·semantic slot을 보존한 직원용 문장으로 변환됨
```

## 검증 순서

1. 구조화 JSON에서 Atom·Relation·Context Signal·Fact 수와 lineage 확인
2. Fact API에서 `PROPOSED → CONFIRMED`, revision, conflict, retry 확인
3. 우측 패널에서 기존 섹션·문장·상태·근거 표시 확인
4. 고객 projection에 `BANK_INTERNAL` 구조화 정보가 유출되지 않는지 확인

