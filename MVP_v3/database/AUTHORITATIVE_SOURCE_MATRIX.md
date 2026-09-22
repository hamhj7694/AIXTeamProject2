# 분석·Context·보고서 기준 원본 매트릭스

기준 시점: 2026-09-22  
범위: `cases.diagnosis_json`, 분석 projection, Context V2, 보고서, 캐시, 거래·금액

이 문서는 같은 의미의 데이터가 여러 테이블에 보일 때 **어느 값이 원본인지**, 나머지는 **조회용 projection·보고서·캐시인지**를 구분한다. 원본이 아닌 값을 직접 수정하거나 자동 합산하지 않는다. 원본이 바뀌면 projection과 캐시는 재생성할 수 있어야 한다.

## 1. 기준 원본 요약

| 데이터 영역 | 기준 원본(source of truth) | 파생·조회 모델 | 캐시/호환 | 쓰기 규칙 |
|---|---|---|---|---|
| 최초 AI 분석 | `cases.diagnosis_json` | `analysis_segments`, `case_semantic_atoms`, `case_semantic_relations`, `case_context_signals`, `context_features` | `case_context_projections.last_success_payload` | 분석 생성 시 원본을 저장하고 projection은 같은 결과에서 생성 |
| 직원 확인·Fact 상태 | `case_context_facts_v2` | Context workspace 응답, support 입력 조립 | 없음(`/facts` legacy route는 410) | 제안·확정·기각·대체는 V2에만 기록. 단, 상태 승격/하락 정책은 별도 제품 결정으로 추적 |
| 미확인·검증 업무 | `case_gaps`, `verification_tasks` | Context workspace와 고객 공유 결과 | 필요 시 projection | 각 업무 테이블에 상태·결과를 기록하고 AI 분석 원본을 덮어쓰지 않음 |
| 담당자 업무·판단 | `actions`, `case_tasks`, `case_decisions` | 타임라인·Context 표시 | 없음 | Action=실제 조치 기록, Task=해야 할 일, Decision=직원 판단으로 분리 |
| LIVE/FINAL 보고서 | `case_reports` + `case_report_sections` | Case bundle의 `live_report`/`final_report` 응답 | 없음 | 보고서 버전·섹션 이력을 보존. 원본 분석과 Fact 원장을 덮어쓰지 않음 |
| Context 표시 편집 | `case_context_items` | 직원 화면 표시 | `case_context_projections` | 표시 문구 편집은 Fact 원장과 분리하고 history에 기록 |
| 거래 목록 | `case_transactions` | `송금 기록 조회` 카드 | Context V2의 직원 확정 실제 금액 사실 | 외부 은행 원장이 아닌 Case 내부 확인 기록. `TRANSFER_OUT`·`RETURN_IN`만 확정 사실에서 승격하고 요구·약속·미확인 진술은 자동 승격하지 않음 |
| 사건 요약 피해금액 | `cases.actual_loss_amount_krw` | 헤더·종결 요약 | 없음 | 사건 단위 단일 요약값. 거래 행을 자동 합산해 덮어쓰지 않음 |

## 2. 분석 원본과 projection 규칙

### `cases.diagnosis_json`

최초 분석 시점의 분석 묶음(요약, 정황, semantic atom/relation, window 등)을 보존하는 원본 snapshot이다. 이후 직원 확인 결과를 여기에 덮어쓰지 않는다. 직원 확인 상태는 `case_context_facts_v2`에서 관리한다. 다만 현재 제품의 상태 승격·하락 규칙을 재설계하는 작업은 별도 체크리스트로 남겨 둔다.

### 분석 projection

- `analysis_segments`: `diagnosis_json.windows`에서 구간 조회용 행으로 생성
- `case_semantic_atoms`: `diagnosis_json.semantic_atoms`에서 의미 단위 조회용 행으로 생성
- `case_semantic_relations`: `diagnosis_json.semantic_relations`에서 관계 조회용 행으로 생성
- `case_context_signals`: `diagnosis_json.context_signals`에서 구조화 신호 조회용 행으로 생성
- `context_features`: 위험도·수치 계산에 필요한 정규화 feature

이 테이블들은 검색·필터·부분 조회를 위한 read model이다. projection 행을 사람이 직접 고쳐 원본 분석을 바꾸지 않는다. 불일치가 발견되면 원본과 projection을 비교하고, 원본에서 projection을 다시 만드는 절차를 사용한다.

## 3. Context V2·보고서·캐시 책임

- `case_context_facts_v2`는 직원이 검토하는 사실 후보와 확인 상태의 기준 원장이다. `diagnosis_json`의 초기 AI 판단과 별개의 후속 업무 상태다.
- `case_reports`/`case_report_sections`는 특정 시점의 LIVE/FINAL 보고서와 버전 이력이다. 보고서가 현재 Fact 원장을 대체하지 않는다.
- `case_context_projections.last_success_payload`는 재생성 가능한 캐시다. 캐시 누락·만료 시 원장과 projection을 이용해 다시 생성해야 하며, 캐시에만 있는 직원 판단을 원본으로 취급하지 않는다.
- `live_report`는 초기 표시 보고서 snapshot이고, `voice_session`은 세션 metadata다. 둘을 우측 Context Panel의 고정 공개 계약으로 사용하지 않는다. 패널 계약은 별도 표시용 모델로 정의한다.

## 4. 금액·거래 책임

`case_transactions`는 여러 거래의 목록이고 `cases.actual_loss_amount_krw`는 사건 단위 요약값이다. `case_context_facts_v2.value_json.amount_krw`와 semantic payload의 금액은 요구·진술·분석 정황이므로 거래 원장에 자동 포함하지 않는다. 거래 중복은 원천 이벤트 ID가 있으면 `source + source_event_id`를 우선하고, 현재 데모는 `case_id + transaction_type + transaction_at(UTC) + amount + account_number + counterparty_account` 정규화 조합을 사용한다. 두 계좌 식별자가 모두 없으면 자동 병합하지 않는다.

## 5. 현재 검증 상태와 후속 항목

읽기 전용 감사 도구:

```powershell
& '.\\.venv\\Scripts\\python.exe' test_HTML_PY\\audit_analysis_consistency.py --database csr
```

- DB 비교(`diagnosis_json` ↔ atoms/windows, orphan, Fact 상태, projection 상태): 현재 71 PASS / 0 WARN / 0 FAIL
- 최신 General API를 격리 포트에서 실행한 smoke: 105 PASS / 0 WARN / 0 FAIL
- MySQL 임시 DB projection lease/revision 통합 테스트: `1 passed` (원본 변경 시 STALE 처리와 마지막 성공 payload 보존 확인)
- 감사 출력은 원문·금액·계좌 값을 포함하지 않고 건수·상태·해시만 기록

아직 실행하지 않은 검증:

- [x] 임시 MySQL DB에서 `case_context_projections` 캐시 삭제 후 원장으로 재생성
- [-] 캐시 삭제와 `case_context_items`·history 보존 추가 검증 — 운영 정책 확정 시 재개
- [-] 보고서/Context 최신 V2 반영 추가 검증 — 우측 패널 구현 시 재개
- [-] Fact 상태 승격·하락 규칙 재설계 — 제품 정책 보류
- [x] `/facts` 내부 호출 제거 및 410 종료 응답 확인
- [-] P2 호환 경로(`voice_sessions`, 첨부 필드) 외부 소비자 0 확인 — 이번 데모 범위 제외

관련 체크리스트는 [`DB_USAGE_AUDIT.md`](DB_USAGE_AUDIT.md)와 [`API_CONTRACT_AUDIT.md`](API_CONTRACT_AUDIT.md)를 따른다.
