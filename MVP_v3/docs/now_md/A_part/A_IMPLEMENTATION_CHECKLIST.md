# CSR v3.1 High-Fidelity Context 구현 체크리스트

작성일: 2026-09-16  
최종 업데이트: 2026-09-17  
목적: 사람이 현재 진행 상황과 다음 작업을 쉽게 확인하기 위한 실행 체크리스트

## 전체 진행 상태

```text
현재 단계: 2.6단계 완료(금액 이벤트·정산 projection 보강)
완료 범위: 입력 채널·데이터 분류 + Atom 추출/보완 + Relation/Signal/Episode 생성 + A 결과 저장 + 중앙 카드 전체 의미 피처 표시 + 핵심 Atom/피처의 Fact projection·근거 연결·직원용 문장화
현재 한계: 전체 semantic slot과 모든 semantic key의 projection, 다중 값 합계 표시, Relation 부재 시 결합 금지 검증, revision/상충 처리, 요약·질문 grounded 검증은 아직 남아 있음
다음 작업: 금액 이벤트 추출·저장·집계 규칙 구현 후 전체 semantic slot/Fact projection과 통합 E2E 검증 진행
진행 원칙: A파트(Context Signal Pipeline) 우선 구현 후 B/C/통합 연결
```

## 2026-09-17 Evaluation and comparison refresh

### Completed evidence
- [x] Official Gold fixtures registered and SHA-256 recorded
- [x] v3.0 corrected-Gold 30-case projection audit executed
- [x] v3.0 comparable recall / precision / F1 recorded: 14.0% / 100.0% / 24.6%
- [x] v3.0 OpenAI token usage measured for 7 features x 3 runs
- [x] v3.0 token baseline recorded: 9,654.67 total tokens / 12 calls (average)
- [x] v3.0 vs v3.1 metric compatibility and non-comparable fields documented
- [x] v3.1 sample structural evidence separated from the not-yet-run full score
- [x] Provider smoke and LIVE replay evidence archived

### Remaining TODO
- [ ] Freeze v3.1 structured output for the same 30 cases / 150 turns
- [ ] Run canonical and high-fidelity mappings together
- [ ] Produce ALL_CASES_WEIGHTED and UNIQUE_SEQUENCE_WEIGHTED scores
- [ ] Produce case-macro F1 and category-macro F1
- [ ] Measure status, polarity, UNKNOWN preservation, and correction resolution
- [ ] Measure relation accuracy, fact-lineage completeness, and section projection accuracy
- [ ] Execute critical contradiction / hallucination / privacy hard gates
- [ ] Repeat v3.1 token, call, and latency measurements three times
- [ ] Calculate token per correct critical fact
- [ ] Run DB persistence, pipeline completion, and browser E2E checks
- [ ] Publish final Notion payload and promote the comprehensive report from DRAFT to FINAL

### Measurement runner added (2026-09-17)
- [x] Added `tests/context_test/compare_v30_v31.py` as the unified comparison evaluator.
- [x] Runner consumes the existing v3.0 corrected-Gold/token artifacts.
- [x] Runner accepts `--v31-output` for the future structured 30-case v3.1 artifact.
- [x] Runner emits explicit `NOT_RUN`, `INCOMPLETE_ARTIFACT`, or `FULL_30_CASE_SCORE` states.
- [ ] Execute the runner with a real v3.1 30-case output after the v3.1 replay is captured.

> 기존 `[x]`는 기본 계약과 1차 구현이 완료되었다는 뜻이다. 아래 `[ ]`는 기존 구현 위에 추가로 필요한 High-Fidelity 2차 개선 TODO이며, 완료 전까지 추정으로 `[x]` 처리하지 않는다.

## 0단계 — 기준과 담당 범위 고정

- [x] High-Fidelity Semantic Context 설계 문서 작성
- [x] 통화·STT 원문 비보관 규칙 정리
- [x] 직원·고객 채팅·카드 답변 원문 보관 가능 규칙 정리
- [x] `Observed → Derived → Confirmed → Reconstructed` 구분
- [x] A/B/C/통합 담당 범위 정리
- [x] 우측 패널 영역별 소유권 정리
- [x] ML feature·artifact 불변 원칙 정리

## 1단계 — 입력 채널·데이터 분류

- [x] 통화·STT 입력과 채팅·카드 입력 분리
- [x] `source_channel` 분류 기준 정의
- [x] `speaker / actor_type` 기준 정의
- [x] `visibility` 기준 정의
- [x] 원문 보존 가능 여부와 보존 정책 정의
- [x] 채팅·카드 답변의 원문 + 구조화 결과 저장 원칙 정의
- [x] 고객용·은행 내부용 정보 격리 원칙 정의

## 2단계 — Semantic Atom 추출 고도화 (A)

- [x] 기존 Event에서 원문 없는 Semantic Atom 병행 출력
- [x] Atom 계약 및 deterministic fingerprint 추가
- [x] Atom 표현·화행·압박·행동 상태 필드 확장
- [x] 기관·역할·주장 Atom 분리
- [x] 한 문장 다중 Atom LLM 출력 schema 추가
- [x] 기존 Event 응답에 semantic_atoms 병행 수신
- [x] 실제 OpenAI 응답 기반 다중 Atom smoke fixture 검증
- [x] 요구·지시·계획·시도·완료 상태 계약 및 요청/지시 정규화
- [x] OTP·비밀번호·PIN·카드 CVC 유형 세분화
- [x] 송금 대상·금액 값·금액 범위·목적 필드 세분화
- [x] 긴급성·의무성·권위 압박·공포 압박 세분화
- [x] 통화 종료 금지·가족 연락 금지·신고 금지 등 고립 신호 분리
- [x] 부정·조건·요구/지시/시도/완료 최소쌍 계약 보존
- [x] 완곡 표현을 목적·대상 코드로 보존하고 반복 압박 강도 필드 검증
- [x] `UNKNOWN / MISSING` 추정 방지 validator
- [x] Atom 수준 원문·민감 literal 비복사 테스트
- [x] Case persistence 경로 원문·민감 literal 비보관 테스트
- [x] 진단 로그·실패 응답 경로 원문·민감 literal 비노출 테스트

### 2단계 추가 개선 TODO — 세분화 피처화 2차

- [x] 한 발화에서 기관·역할·주장·요구·위협·목적·행동을 독립 Semantic Atom으로 분리하는 schema·지침·검증 완료
- [x] 같은 발화의 다중 predicate를 하나의 Atom으로 합치지 않도록 primary predicate·혼합 슬롯 validator 추가
- [x] actor/subject/target/destination 슬롯의 허용 코드 검증 및 누락·혼합 방지
- [x] `REQUESTED`·`INSTRUCTED`·`PLANNED`·`ATTEMPTED`·`REPORTED_ACTION`·`VERIFIED`·`UNKNOWN` 세분화
- [x] `POLARITY`·`MODALITY`·`CLAIM_STATUS`·`VERIFICATION_STATUS` 동시 보존 계약 확인
- [x] `amount_scope`·`amount_value_krw`·`claimed_purpose`·`threat_type`·`auth_secret_type` 독립 보존
- [x] 동일 의미라도 실제 표현이 다른 `observed_terms` lexical distinction 보존
- [x] source에 없는 observed term 생성 방지 및 source 검증 validator 강화
- [x] 통화 한 건에서 여러 금액·여러 행동·여러 요구를 모두 보존하는 fixture 확장
- [x] 세부 피처화 결과의 Atom/Relation/Context Signal coverage 리포트 추가

## 2.5단계 — Semantic Feature Audit Agent (A)

> 2단계에서 생성된 Semantic Atom·Observed Term·Expression Feature가 누락되거나 혼합되지 않았는지 검사한다. 감사 결과는 원본 결과를 직접 덮어쓰지 않고 `PASS / NEEDS_REVIEW / REEXTRACTION_REQUIRED`로 별도 기록한다.

- [x] `SemanticAuditResult` 계약 및 schema version 정의
- [x] Atom 필수 슬롯·predicate·action state·polarity·modality 일관성 검사
- [x] 다중 금액·다중 요구·다중 주장 누락 검사
- [x] `observed_terms` source 존재·allowlist·길이·민감 literal 검사
- [x] 원문에 없는 lexical cue 및 unsupported semantic feature 탐지
- [x] Atom·Relation·Context Signal lineage 및 orphan reference 검사
- [x] Semantic Coverage·Aggregation Loss·Unsupported Lexicalization 지표 산출
- [x] 누락된 턴만 targeted re-extraction하는 보완 경로 정의
- [x] 감사 결과 JSON export 및 터미널 조회 명령 추가
- [x] 원본 분석 결과 자동 확정·삭제를 하지 않는 human review 경계 테스트

## 2.6단계 — 금액 이벤트·정산 Projection 보강 (A + 통합) ✅ 완료

> 여러 금액 발언을 단순 합산하지 않고, 요구·실제 송금·반환·최종 피해 주장으로 분리한다. 기존 추천/Fact를 삭제하지 않으며, 직원 검토 상태와 근거를 유지한다.

- [x] `TRANSFER_OUT`·`REFUND_IN`·`REQUESTED_AMOUNT`·`CLAIMED_LOSS` 금액 이벤트 타입 분리
- [x] 금액 단위(`만원`·`천만원`·`억원`)를 원화 정수로 정확히 변환하고 단위 근거 보존
- [x] 송금(OUT)·반환(IN) 방향과 금액 역할을 추출 결과에 저장
- [x] `추가`·`총`·`누적`·`최종`·`결과적으로` 표현의 의미 분리
- [x] 반환 합계는 송금 합계에 더하지 않고 `송금 합계 - 반환 합계`로 순손실 계산
- [x] 요구 금액·실제 송금액·반환액·순손실을 패널 요약에서 별도 표시
- [x] 여러 금액 이벤트를 동일 Fact로 덮어쓰지 않고 event_id/turn/evidence 기준으로 보존
- [x] 부정·정정·불확실 금액은 현재 합계에서 제외하거나 확인 필요로 표시
- [x] 중앙 Copilot과 Context Panel이 동일한 Money Event/Atom projection을 사용하도록 연결
- [x] `300만원 요구받았다`, `300만원 송금했다`, `20만원 돌려받았다`, `5만원 추가 송금했다` 회귀 fixture 추가
- [x] 직원 확정 전 AI 추천 합계와 직원 확정 합계를 구분 표시
- [x] `PROPOSED` AI 추천 금액은 공식 합계·순손실 계산에서 제외
- [x] `CONFIRMED` 직원 채택 금액만 공식 합계·순손실 계산에 포함
- [x] `REJECTED`·`SUPERSEDED` 금액은 공식 계산에서 제외하고 이력으로만 보존
- [x] 실제 송금·반환은 `CONFIRMED` 이벤트끼리 각각 합산
- [x] 요구 금액·최종 피해 주장은 기본적으로 최신 확정값 1건 정책 적용
- [x] `총`·`누적`·`추가`가 명시된 경우에만 요구 금액 누적 계산
- [x] 패널에 `직원 확정 금액`과 `AI 추천·확인 필요` 영역을 분리 표시
- [x] 직원 확정 전에는 `확정 0건`과 추천 건수를 혼동하지 않도록 표시

## 3단계 — Relation·Context Signal 생성 (A)

- [x] Atom 간 `SUPPORTS` 관계 추출(기관 주장→직책 주장)
- [x] `JUSTIFIES / REQUIRES / CAUSES` 규칙 추가(위협·인증정보·압박→행동)
- [x] `CONDITIONAL_ON / CONTRADICTS` 관계의 보수적 규칙 검증
- [x] conversation episode·action group 구성(동일 턴·동일 predicate 기준)
- [x] entity registry 구성(명시적 코드만; 자유문자 coreference 추정 금지)
- [x] Context Signal DTO 정의
- [x] Signal → source Atom lineage 연결
- [x] 사칭·송금 유도·압박·고립 복합 패턴의 결정적 signal 생성
- [x] Signal severity·confidence·visibility 필드 정의
- [x] 관계 hallucination 차단 테스트(교차 턴 연결 금지)

## 4단계 — Fact·DB 저장 계약 (A + 통합)

- [x] Semantic Atom 저장 리소스 설계 및 Case 생성 트랜잭션 저장
- [x] Context Signal 저장 리소스 설계 및 Case 생성 트랜잭션 저장
- [x] 초기 Fact의 STRUCTURED_SIGNAL/Atom support lineage 연결
- [x] AI 결과의 초기 Fact `PROPOSED` 저장
- [x] 직원 확인 시 `CONFIRMED` 전환
- [x] 수정 시 revision/supersede 처리
- [x] 상충 주장 conflict 처리
- [x] retry·idempotency·fingerprint 처리
- [x] 통화 원문 비보관 persistence 테스트
- [x] 채팅 원문 보관·visibility 테스트

## 5단계 — A 담당 Context Panel Projection

- [x] 사칭 기관 Atom의 관찰 기관명(예: 검찰청)을 일반 라벨로 잃지 않고 패널 Fact에 보존·표시
- [x] 개인정보·상대방 요구·압박·사건 주장 Fact에도 privacy-safe `observed_terms` 보존
- [x] 패널 문장화에서 관찰 표면어를 우선 사용하고 없을 때만 일반 라벨 fallback
- [x] 관찰 키워드 projection 회귀 테스트 보강(`test_atom_fact_projection.py`)

- [x] 피해·노출 핵심 피처 projection 연결(인증정보·개인정보·기기·금액·실제 이체 상태)
- [x] 사칭·접촉 정보 핵심 projection 연결(기관 사칭·통화/외부 연락 통제)
- [x] 사기 정황 핵심 projection 연결(주장·송금·링크·안전계좌·압박·고립)
- [x] 사실·확인 현황에 A Fact 표시
- [x] Fact의 Atom/Signal lineage 보존 및 직원용 근거 문장 표시
- [x] AI 제안·확인 필요·확정·제외 상태 표시
- [x] 중앙 `analysis-result created` 카드에 직원용 의미 피처 표시
- [x] 우측 Context Panel에 모든 의미 피처를 기존 섹션 Fact로 projection
- [x] 다중 금액·다중 요구·다중 주장 목록과 합계/개별 값 표시
- [x] 고객 화면에 `BANK_INTERNAL` 구조화 정보 미노출

### 5단계 추가 개선 TODO — 세부 Fact projection

- [x] 모든 Semantic Atom을 기존 7개 패널 섹션의 적절한 Fact로 매핑
- [x] 하나의 broad `circumstance.demand`에 여러 요구를 합치지 않고 개별 Fact 생성
- [x] 하나의 broad `circumstance.tactic`에 여러 압박 수법을 합치지 않고 개별 Fact 생성
- [x] 서로 다른 금액·목적·대상·기관별 Fact separate projection
- [x] `communication_control` 유형별 Fact와 직원용 문장 분리
- [x] Atom의 `observed_terms`를 근거로 한 privacy-safe 문장 specificity 연결
- [x] Fact별 Atom provenance 연결(`STRUCTURED_ATOM` reference)
- [x] 패널 deduplication이 세부 semantic slot을 손실시키지 않는지 검증

## 6단계 — Grounded 문장화

- [x] Fact 기반 직원용 Grounded 문장 plan(상태·허용 semantic key 보존)
- [x] 패널 문장에 Fact evidence/Atom lineage 연결
- [x] 사건 요약 근거 제한
- [x] 확인 질문 근거 제한
- [x] Context Panel 문장 생성
- [x] `CLAIMED → VERIFIED` 변질 차단
- [x] `REQUESTED → COMPLETED` 변질 차단
- [x] `UNKNOWN → 구체값` 추정 차단
- [x] 부정·조건·긴급성 보존 Validator
- [x] one Fact / one semantic statement 기본 정책(패널 Fact별 개별 projection)
- [x] 전체 Semantic slot preservation 적용
- [x] 핵심 `observed_terms` 기반 specificity preservation(OTP·안전계좌·긴급성)
- [x] 핵심 Action State별 문장 template 적용(요구·고객 진술·미확인)
- [x] UNKNOWN / NEGATIVE / CONDITIONAL preservation validator
- [x] `communication_control` 세부 유형별 문장화
- [x] 다중 Fact separate statement projection 및 specificity 유지
- [x] Relation 없는 Fact의 임의 연결 차단(명시적 supporting Atom만 사용)
- [x] broad abstraction / semantic broadening validator
- [x] Fine-Grained Grounded Statement regression test

> 2026-09-16 진행 기록: `atom_fact_projection.py`를 추가해 Semantic Atom별 독립 Fact 후보와 Atom lineage를 연결했고,
> 패널 dedup 기준을 source Atom 단위로 보강했다. 상세 결과와 남은 raw persistence fixture 정리는
> `A_4_TO_6_PROGRESS_20260916.md`에 기록했다.

### 6단계 추가 개선 TODO — 문장화 고도화

- [x] Statement Plan을 실제 내부 projection 계약으로 구현
- [x] one Fact / one Statement 기본 정책을 전체 semantic key에 적용
- [x] 모든 semantic slot이 문장화 전후 동일한지 검증
  - 운영 웹 UI/API에는 노출하지 않고, 성능·회귀 테스트와 내부 JSON 리포트에서만 사용
- [x] `REQUESTED`와 `INSTRUCTED` 문장 표현 분리
- [x] `CUSTOMER_REPORTED_COMPLETED`를 `VERIFIED COMPLETED`로 승격하지 않는 검증
- [x] `UNKNOWN`·`DENIED`·`NEGATIVE`·`CONDITIONAL` 보존 validator 완성
- [x] `observed_terms`가 없을 때 surface 표현을 임의 생성하지 않는 검증
- [x] Relation이 없을 때 두 Fact를 인과·목적 문장으로 연결하지 않는 검증
- [x] Context Signal label보다 supporting Atom/Fact를 우선하는 문장화 검증
- [x] Semantic Broadening Rate·Aggregation Loss Rate 측정 테스트 추가
- [x] Unsupported Lexicalization Rate 측정 테스트 추가

> 2026-09-16 진행 기록: `case_support/grounding.py`를 추가해 Case Brief의 risk evidence가
> Diagnosis Evidence에서만 유래하는지, 확인 질문이 미확인 항목과 허용된 이벤트 유형에만 연결되는지 검증한다.

## 6.5단계 — A파트 테스트·품질 평가·파이프라인 구조화

> 1~6단계의 결과를 운영 화면에 추가로 노출하는 단계가 아니다. 추출·감사·저장·문장화·패널 반영 전 과정을
> 재현 가능한 fixture, JSON 리포트, 지표, 도표, E2E 테스트로 평가하고 다음 개선의 근거를 남기는 내부 품질 게이트다.
> 원문·민감 literal은 리포트와 산출물에도 저장하지 않는다.

현재 상태: **부분 완료** — 평가 설계·JSON/한국어 보고서 생성·구조 지표 산출·평가기는 완료했지만,
정답 annotation 확정 후의 실제 Precision·Recall·F1, 오탐·미탐 평가, DB 저장 검증과 운영 패널 E2E는 미완료다.
따라서 이 단계 전체를 완료로 표시하지 않는다.

- [x] 6.5단계 범위·산출물 보관 위치·웹 비노출 원칙 정의
- [x] 기준 fixture 세트와 정답 annotation 계약 템플릿 추가
- [x] v3.0 `benchmark_v1.0` atomic fact를 v3.1 partial gold seed로 변환하는 어댑터 추가
- [x] Event·Semantic Atom·Observed Term·Expression Feature 구조 JSON export 스크립트 추가
- [ ] Atom→Relation→Context Signal→Fact→Grounded Statement lineage JSON export
- [ ] 추출 AI 정확도 지표(precision·recall·F1·critical slot coverage) 실제 산출
- [ ] v3.0과 직접 비교 가능한 지표의 v3.1 재집계
- [x] v3.0 baseline과 v3.1 현재 구조를 나란히 보여주는 JSON·한국어 비교 보고서 생성
- [ ] 세부 피처·키워드 보존율과 누락·과잉 추출 지표 산출
- [x] 점검 AI 발동 조건과 `PASS / NEEDS_REVIEW / REEXTRACTION_REQUIRED` 기준 문서화
- [ ] 점검 AI 오탐·미탐 confusion matrix 및 human review 기준 산출
- [ ] targeted re-extraction 전후 회복률·불필요 재추출률 산출
- [ ] 최종 Feature/Fact의 다중 값 보존·합산·중복 제거 지표 산출
- [x] DB 저장 성공·transaction rollback·idempotency·revision 관련 회귀 테스트 실행
- [ ] 원문 비보관·민감 literal 제거·visibility 격리 검사
- [x] 문장화 semantic slot preservation·polarity·modality·action state 일치율 산출
- [ ] 원문 의미와 재구성 문장의 semantic fidelity 평가(원문 자체 저장 없이 annotation 비교)
- [ ] 우측 Context Panel 기존 섹션 projection 및 문장 표시 E2E 검증
- [x] 텍스트 입력부터 Case Room 생성까지 파이프라인 sequence/data-flow 도표 작성
- [ ] 동일 fixture 재실행 시 fingerprint·지표 차이 비교 리포트 작성
- [x] 성능·실패·재시도·부분 성공·관측성 기준과 실행 명령 문서화
- [x] JSON artifact privacy scan 구현 및 샘플 PASS 확인
- [x] 동일 결과 비교용 Atom fingerprint/count diff 도구와 회귀 테스트 추가

상세 체크리스트와 산출물 규격은 [`A_6_5_TEST_AND_PIPELINE_CHECKLIST.md`](A파트%20테스트%20및%20파이프라인%20구조%20정리/A_6_5_TEST_AND_PIPELINE_CHECKLIST.md),
평가 설계는 [`A_6_5_TEST_AND_PIPELINE_DESIGN.md`](A_6_5_TEST_AND_PIPELINE_DESIGN.md)에 기록한다.
6.5단계 최종 산출물은 [`A_6_5_FINAL_A_PART_COMPREHENSIVE_REPORT.md`](A파트%20테스트%20및%20파이프라인%20구조%20정리/A_6_5_FINAL_A_PART_COMPREHENSIVE_REPORT.md)로 작성한다.

## 7단계 — B파트 연동

- [ ] 미확인 Fact 기반 고객 질문 생성
- [ ] 이미 확인된 내용 질문 제외
- [ ] AI 선택지 생성
- [ ] 다중 선택 답변 지원
- [ ] 직접 입력 답변 지원
- [ ] 질문 답변 원문과 구조화 결과 저장
- [ ] 기관 확인 리스트·확인 방법 추천 연동
- [ ] 고객용·은행용 Copilot visibility 검증

## 8단계 — C파트 연동

- [ ] A Signal/Fact 기반 사건 요약
- [ ] 은행 Brief 생성
- [ ] 조치 기록·업무 카드 추천
- [ ] 고객 공유 결과 생성
- [ ] 최종 보고서 생성
- [ ] 문장별 근거 연결

## 9단계 — 통합 Orchestrator

- [ ] AI 호출 순서 정의
- [ ] 복합 사건별 호출 계획 정의
- [ ] A/B/C 결과 공용 DTO 연결
- [ ] Case 반영 트랜잭션 정리
- [ ] 실패·재시도·부분 성공 정책 정리
- [ ] 중복 호출·중복 저장 방지

## 10단계 — 테스트·평가

- [ ] Atom decomposition 정확도
- [ ] Semantic Coverage
- [ ] Specificity Preservation
- [ ] Statement Specificity Preservation
- [ ] Semantic Slot Preservation
- [ ] Aggregation Loss Rate
- [ ] Semantic Broadening Rate
- [ ] Relation Preservation
- [ ] Modality Preservation
- [ ] Action-State Preservation
- [ ] Polarity Preservation
- [ ] Unknown Preservation
- [ ] Lexical Cue Preservation
- [ ] Observed-Term Preservation
- [ ] Relation Faithfulness
- [ ] Unsupported Lexicalization Rate
- [ ] Unsupported Claim Rate
- [ ] Contradiction Rate
- [ ] Critical Signal / Fact Recall
- [ ] Risk Detection Precision / Recall / F1
- [ ] Customer/Bank Role Isolation
- [ ] Question Duplicate Rate
- [ ] Critical Question Coverage
- [ ] 중앙 카드·우측 패널 E2E 검증

### 개발자 확인·리포트 TODO

- [ ] 특정 Case의 전체 `DiagnosisResult`를 터미널에서 조회하는 명령 추가
- [ ] Event·Semantic Atom·Observed Terms·Expression Features 출력
- [ ] Relation·Context Signal·Fact·Grounded Statement 연결 출력
- [ ] 민감정보·원문·긴 phrase가 리포트에 포함되지 않는 검증
- [ ] 분석 결과를 개발자용 JSON 파일로 export
- [ ] JSON 리포트 schema/version 및 생성 시각 기록
- [ ] 동일 Case를 재분석했을 때 Atom fingerprint와 세부 피처 차이 비교

## 현재 구현 기록

### 완료

- runtime risk threshold를 환경변수 `WINDOW_RISK_THRESHOLD=0.60`으로 적용
- ML artifact 내부 threshold `0.95`와 feature 구조 유지
- `SemanticAtom` 계약 추가
- 기존 Event → 원문 없는 Semantic Atom 병행 adapter 추가
- Atom에 화행·의무성·긴급성·압박·통제·인증정보·금액 범위 필드 추가
- 사칭 기관·직책과 정확한 원화 금액 전용 필드 추가
- 기존 turn별 LLM 응답 schema에 다중 `semantic_atoms` 배열 추가
- 실제 OpenAI 호출에서 기관·직책·통화 종료 금지·가족 알림 금지·전액 송금 분해 확인
- LLM이 핵심 Atom을 누락할 경우 기존 Event에서 해당 신호만 보완하는 병합 안전망 추가
- `OPENAI_EVENT_MAX_OUTPUT_TOKENS=1800` 실측 조정(전체 진단 16,000토큰 상한 유지)
- Semantic Atom·Relation·Context Signal 전용 저장 리소스와 Case 생성 경계 저장 연결(migration 017)
- 다중 요구 금액 보존과 초기 요구 금액 Fact의 개별 생성 연결
- 초기 Fact의 관련 Atom lineage 보정 및 은행용 근거 문장 projection 추가
- 중앙 `analysis-result created`를 직원용 주요 정황·세부 피처 전체 표시 구조로 변경
- 은행 화면에서 개발자용 Atom/Relation/Signal 코드·신뢰도·내부 개수를 숨기는 표현 계층 적용
- supporting Atom의 구조화 슬롯을 참조하는 세분화 Grounded Statement 1차 적용
- OTP 유형, 안전계좌 목적, 긴급성 observed term, 가족·은행 연락 통제별 직원용 문장 projection 추가
- 기존 Fact별 dedupe를 유지하면서 서로 다른 supporting Atom 의미가 합쳐지지 않도록 문장 결과를 분리

## v3.1 AI 분석 예산 조정 (2026-09-16)

## 문서·폴더 운영 규칙

- `now_md` 기준 문서 작업에서 `migrations/18` 폴더를 새로 만들지 않는다.
- migration이 필요해 보여도 기존 migration 체계와 통합 담당자의 확인 없이 임의 생성하지 않는다.

- [x] 세분화된 Semantic Atom·관계·그룹화 파이프라인에 맞춰 1회 분석 호출 한도 상향
- [x] `OPENAI_MAX_CALLS_PER_DIAGNOSIS=64` 적용
- [x] `OPENAI_MAX_TOTAL_TOKENS_PER_DIAGNOSIS=32000` 적용
- [ ] 실제 분석별 호출 수·토큰 사용량 측정 후 운영 한도 재조정
- [ ] 내부 예산 초과와 OpenAI 실제 quota 초과 오류를 UI에서 구분 표시

## 시간대 일괄 정리 (2026-09-16)

- [x] MySQL 저장소의 생성·수정 시각을 UTC aware 기준으로 통일
- [x] Context projection 저장 시각도 UTC 기준으로 통일
- [x] API는 UTC ISO 시각을 반환하고 프론트는 Asia/Seoul로 표시하는 규칙 유지
- [x] 시간대 회귀 테스트 `test_case_created_at_timezone.py` 통과
- [ ] 기존 DB에 이미 저장된 잘못된 시각은 보정 전 데이터 기준 확인 후 별도 마이그레이션 여부 결정
- LLM Atom은 원문을 복사하지 않도록 전용 지침 추가
- 요구·지시·시도·완료·거부·조건 및 `UNKNOWN` 최소쌍 회귀 테스트 추가
- General API Case persistence에서 통화 원문 비보관 테스트 재통과
- 진단 실패 응답과 request trace 로그에서 입력 원문 비노출 테스트 추가
- AI API 전체 회귀 테스트 수행(최종 수치는 아래 최근 갱신 참조)
- 설계 문서에 채널별 원문 보관 규칙과 A파트 담당 범위 반영

### 다음 작업

1. Fine-Grained Grounded Statement와 one-Fact-one-Statement projection 구현
2. 전체 semantic key를 `피해·노출`, `사칭·접촉 정보`, `사기 정황` Fact로 projection
3. 다중 금액·다중 요구·다중 주장 separate statement와 합계·개별 값의 패널 표시
4. UNKNOWN/NEGATIVE/CONDITIONAL 및 semantic broadening validator 구현
5. Fact revision/supersede/conflict와 retry·idempotency 검증
6. 사건 요약·확인 질문까지 grounded 근거 제한 확장
7. 개발자용 Atom·Relation·Signal·Fact Markdown 리포트 export
8. 2.5단계 Semantic Feature Audit Agent 구현 및 누락 피처 targeted re-extraction

### 2.5단계 실행 명령

```powershell
cd MVP_v3/backend
..\.venv\Scripts\python.exe scripts\export_diagnosis_report.py --input .\sample-transcript.txt --output .\diagnosis-report.json
```

`diagnosis-report.json`에는 Semantic Atom·Observed Terms·Expression Features·Relation·Context Signal·Audit 결과가 포함되며, 개발자 export에서는 통화 원문·Event evidence 문장·Window 원문을 제거한다.

### 최근 갱신 (2026-09-16)

- 1단계 입력 채널·데이터 분류 완료
- 2단계 Atom 세부 필드(화행·압박·통제·인증정보·금액 값/범위) 추가
- 실제 OpenAI 연결 성공 및 다중 Atom 분해 확인(`LIVE_AI_READY`)
- 응답 변동으로 송금 Atom이 누락된 사례를 발견해 Event 기반 선택적 보완 적용
- 상태·부정·조건·UNKNOWN 최소쌍 테스트 `8개` 추가
- General API 저장 경계 회귀 테스트 `15 passed, 3 subtests passed`
- AI API 전체 회귀 테스트 `131 passed, 30 subtests passed`
- Relation·Signal 초기 builder 및 교차 턴 hallucination 차단 테스트 `31 passed, 2 subtests`
- `JUSTIFIES / REQUIRES / CAUSES` 관계 테스트 포함 Semantic Atom 테스트 `22 passed`
- conversation episode·action group·entity registry 초기 builder 추가 및 테스트 `21 passed`
- OTP·PASSWORD·PIN·CARD_CVC 및 압박 차원 세부 검증 테스트 `19 passed`
- 직원용 중앙 분석 결과 UI 문장화 및 전체 의미 피처 표시 적용
- 핵심 Fact를 직원용 문장으로 변환하고 상태 승격을 차단하는 grounded layer 추가
- 기관 사칭·송금·링크·안전계좌·고립·긴급 정황의 핵심 Fact projection 및 의미 중복 제거 적용
- 우측 패널 Fact 근거에 연결된 Atom/Signal 요약과 privacy-safe 문장 표시 적용
- 프론트엔드 typecheck 및 Vite production build 통과
- General API Context Panel 및 grounded 문장화 테스트 7개, 전체 선택 회귀 테스트 16개 통과
- 다음 확인 대상은 전체 Fact projection, 다중 값 합계, 요약·질문 grounded 검증

## 6단계 validator 보강 완료 기록 (2026-09-17)

- [x] `UNKNOWN / MISSING` 상태가 문장화 과정에서 구체적인 사실로 승격되지 않도록 차단
- [x] `broad abstraction / semantic broadening` 검사로 금액·기관·인증정보·목적의 구체 슬롯 손실 차단
- [x] 문장화 전후 핵심 semantic slot 보존 검사 연결
- [x] 위 검사는 운영 웹 UI/API에 추가 노출하지 않고 내부 품질·회귀 테스트에서만 실행
- [x] `test_grounded_semantic_validation.py` 회귀 테스트 11건 통과

## 현재 테스트 가능 범위

- [x] 터미널에서 AI API의 `DiagnosisResult`와 Atom/Relation/Signal 생성 결과를 테스트 가능
- [x] Case API에서 privacy-safe 구조화 결과만 JSON으로 조회 가능
- [ ] Atom·Relation·Signal·Fact를 한 번에 읽는 Markdown 개발자 리포트 export
- [x] Case 생성 경계에서 원문 비보관 동작 테스트 가능
- [x] 중앙 생성 결과 카드에 직원용 의미 피처 표시
- [x] 우측 Context Panel 핵심 Fact를 직원용 문장과 근거로 표시하는 연결
- [x] 전용 Case DB 리소스와 초기 revision/PROPOSED Fact 저장 연결

현재는 A 결과 저장, 중앙 카드의 전체 의미 피처 표시, 핵심 Fact의 직원용 문장화 및 우측 패널 근거 연결까지 검증 대상이다. Atom이 저장되면 핵심 의미는 Fact로 projection되어 패널에 표시되지만, 전체 semantic key coverage와 Fact revision/supersede/conflict, 중앙 카드·우측 패널의 완전한 E2E 동일 revision 검증은 다음 작업으로 남아 있다.

### 2026-09-16 최신 확인 — VP-18

- Diagnosis 결과: Event 5개, Semantic Atom 9개, Relation 2개, Context Signal 0개
- `Context Signal 0개`는 실패가 아니라 복합 신호 생성 조건을 충족한 조합이 없다는 의미
- 우측 패널에는 기관 사칭, 인증정보, 송금·이체, 링크·앱 실행, 안전계좌 목적, 고립·긴급 정황이 직원용 문장 Fact로 표시됨
- 동일 의미의 기존 Fact와 Atom-derived Fact는 패널에서 중복 문장을 만들지 않도록 합쳐짐
- Context Signal 0개는 여전히 복합 신호 생성 조건 미충족을 뜻하며, 개별 Atom·Fact projection 실패를 뜻하지 않음
- 아직 남은 범위는 전체 semantic key coverage, 다중 값 합계/편집, revision·상충 처리, 요약·질문 grounded 검증임

## 2026-09-16 LLM Context lexical/pragmatic 보강

- [x] 기존 normalized `lexical_cues`를 유지하면서 Atom 전용 `observed_terms` 추가
- [x] 실제 입력에 존재한 allowlist 핵심 용어만 surface form·lemma·normalized lexical code로 보존
- [x] `speech_form_codes`와 urgency·obligation·directive strength를 deterministic post-process로 보강
- [x] Context observation에는 surface form을 중복 저장하지 않고 `source_atom_ids`·`observed_lexical_codes`·`semantic_features`만 연결
- [x] OTP·계좌번호 등 민감 literal, raw phrase, 일반 토큰 dump, 원문에 없는 용어를 저장하지 않는 targeted test 추가
- [x] ML feature 이름·순서·개수·shape·preprocessing·artifact와 Frontend는 변경하지 않음
- [x] 기존 JSON payload에 additive field만 추가하므로 DB migration 불필요

이번 작업의 적용 범위는 A파트 LLM Context branch와 공용 Diagnosis 계약이다. `observed_terms`의 surface form은 짧은 allowlist와 source 존재 검증을 통과한 값만 Atom에 귀속되고, Case-level Context Feature는 Atom lineage를 참조한다. 현재 working tree의 `now_md`에는 `A_IMPLEMENTATION_CHECKLIST.md`와 `A_HIGH_FIDELITY_SEMANTIC_CONTEXT_DESIGN.md`만 존재하며, 작업 프롬프트에 지정된 README·P0 fixture·개선 방향·상태 감사 문서는 현재 트리에서 확인되지 않았다.

## 변경 시 기록 규칙

- 단계가 끝날 때마다 이 파일의 체크박스를 갱신한다.
- 코드·DB·API·Frontend를 변경하면 변경 파일과 테스트 결과를 `현재 구현 기록`에 추가한다.
- 설계와 구현이 달라지면 설계 문서에도 결정 사항을 함께 기록한다.
- 완료되지 않은 항목은 `[ ]`로 유지하고 추정으로 `[x]` 처리하지 않는다.
# 2.6 추가 반영 — 금액 요약 노출 규칙 (2026-09-17)

- [x] `context-amount-summary`는 직원이 확정한 금액 Fact가 하나 이상일 때만 렌더링
- [x] `PROPOSED` AI 추천 금액은 요약 합계·건수에서 제외하고 개별 Fact에서만 확인
- [x] 확정 금액의 요구·실제 송금·반환·순손실만 공식 요약에 표시

## 2.6 최종 완료 판정 (2026-09-17)

아래 목록을 2.6단계의 최종 판정 기준으로 사용한다. 기존 초안 TODO와 중복되는 항목은 이 목록의 상태가 우선한다.

- [x] `TRANSFER_OUT`·`REFUND_IN`·`REQUESTED_AMOUNT`·`CLAIMED_LOSS` 금액 역할을 구조화 값으로 보존
- [x] 금액 단위 정규화 및 `amount_scope(EVENT/FINAL/CUMULATIVE)` 보존
- [x] 반복 금액을 하나의 Fact로 합치지 않고 `amount_event_id`·Atom·turn 근거로 분리
- [x] 직원 확정(`CONFIRMED`) 금액만 공식 요약·순손실 계산에 반영
- [x] AI 추천(`PROPOSED`) 금액은 공식 합계에서 제외하고 개별 Fact로만 노출
- [x] 반환 금액은 실제 송금과 분리하고 순손실을 `송금 합계 - 반환 합계`로 계산
- [x] 최종 표현이 명시된 요구 금액은 `FINAL` 우선 정책으로 표시
- [x] Copilot과 Context Panel이 동일한 privacy-safe `money_events` 구조를 사용하도록 공통 계약 연결
- [x] 금액 추출·Atom projection·Copilot projection 회귀 테스트 완료

# 제외 정보 완전 삭제 기능 (2026-09-17)

- [x] 제외(`REJECTED`) Fact에만 완전 삭제 버튼 노출
- [x] 삭제 전 확인 모달 적용
- [x] `expected_version` 검증 및 `HARD_DELETE` 감사 tombstone 기록
- [x] 삭제 후 Context Panel 재조회
- [x] 제외된 Fact 전 항목(피해·노출, 사칭·접촉, 사기 정황, 사실·확인)의 복구·완전 삭제 동작 연결
> 6.5단계와 v3.0→v3.1 측정의 단일 최신 기준은 `A파트 테스트 및 파이프라인 구조 정리/A_6_5_MASTER_CHECKLIST.md`다. 본 문서는 구현 이력으로 보존한다.
