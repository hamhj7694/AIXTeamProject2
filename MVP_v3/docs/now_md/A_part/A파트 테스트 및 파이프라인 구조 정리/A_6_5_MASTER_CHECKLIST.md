# A파트 6.5단계·v3.0/v3.1 공식 측정 마스터 체크리스트

최종 업데이트: 2026-09-17  
문서 상태: **진행 중 — v3.1 전체 측정 전**  
이 문서는 A파트의 6.5단계 테스트, 파이프라인 검증, v3.0 baseline, v3.0→v3.1 비교 작업을 묶은 단일 기준 문서다.

기존 체크리스트와 설계 문서는 근거·이력 문서로 보존한다. 완료 상태와 다음 작업을 판단할 때는 이 문서를 우선한다.

## 1. 상태 표기

| 상태 | 의미 |
|---|---|
| `DONE` | 저장소의 코드·실행 로그·산출물로 확인됨 |
| `PARTIAL` | 일부 fixture 또는 샘플만 확인됨 |
| `NOT RUN` | 실행 코드 또는 조건은 있으나 실제 결과 산출물이 없음 |
| `BLOCKED` | 실행에 필요한 서버·provider·DB·사람 승인 등이 없음 |
| `HUMAN REQUIRED` | Codex가 대신 확정하면 안 되는 판단 |

`NOT RUN`과 `BLOCKED`는 0점이 아니다. 점수를 만들 수 없는 상태를 기록한 것이다.

## 2. 현재 확인된 기준선

### 2.1 Dataset / Gold

- [x] 공식 benchmark fixture: 30 cases / 150 turns
- [x] 시나리오 분포: HIGH 10 / MIXED 10 / LOW 10
- [x] 공식 Gold 3종 등록 및 SHA-256 기록
- [x] v3.0 공식 기준 commit: `071fb512ce42a570b0bcf585041eac6f31c2fb1c`
- [ ] Atom·Relation·Signal·Fact·Statement 전체 human annotation 확정
- [ ] 다중 금액·다중 요구·부정·조건·정정·완료 상태 fixture의 annotation 검토

### 2.2 v3.0 측정 결과

- [x] corrected-Gold comparable projection audit 실행
- [x] v3.0 comparable Recall: **14.0%**
- [x] v3.0 comparable Precision: **100.0%**
- [x] v3.0 comparable F1: **24.6%**
- [x] v3.0 token usage: 7 features × 3 runs, 21 LIVE runs, 36 calls
- [x] v3.0 평균 token baseline: **9,654.67 total tokens / 12 calls**
- [ ] v3.0 unique-sequence weighted score
- [ ] v3.0 latency P50/P95/MAX

### 2.3 v3.1 현재 상태

- [x] v3.1 high-fidelity Gold fixture 등록
- [x] 구조 샘플 확인: Event 5 / Atom 9 / Relation 2 / Context Signal 0
- [x] VP-18 샘플 lineage: Event→Atom 1.0, Relation 1.0, Context Signal 1.0
- [ ] 동일 30 cases / 150 turns v3.1 raw structured output
- [ ] v3.1 전체 Precision / Recall / F1
- [ ] v3.1 case macro F1 / category macro F1
- [ ] v3.1 safety hard gates
- [ ] v3.1 token / calls / latency 3회 반복

## 3. 역할별 책임

### 3.1 Codex가 수행할 일

- [x] fixture hash, dataset profile, v3.0 baseline 산출물 확인
- [x] v3.0 corrected-Gold evaluator 실행
- [x] v3.0 token measurement 결과 정리
- [x] `compare_v30_v31.py` 통합 비교기 작성 및 dry-run
- [ ] v3.1 replay 실행 및 raw structured JSON 보관
- [ ] canonical / high-fidelity Gold 매핑과 모든 지표 계산
- [ ] case/category macro, correction, relation, lineage, projection 지표 계산
- [ ] contradiction / hallucination / privacy hard gate 실행
- [ ] token/call/latency 반복 측정 및 `token_per_correct_critical_fact` 계산
- [ ] DB persistence / pipeline completion / API·browser E2E 실행
- [ ] metric JSON, diff report, privacy scan, Notion 전달용 payload 갱신

### 3.2 사람이 확인·결정해야 할 일

- [ ] Gold annotation이 실제 의도와 맞는지 승인
- [ ] 정정·부정·요구/수행/완료처럼 의미가 뒤집히는 critical fixture 판정
- [ ] 직원용 grounded statement의 자연스러움·의미 일치성 검토
- [ ] privacy-safe export와 고객/은행 visibility 정책 최종 승인
- [ ] v3.1 비교에 사용할 commit·model·환경변수·temperature 고정 승인
- [ ] hard gate 기준과 최종 발표 acceptance 기준 승인
- [ ] `FINAL` 보고서 및 Notion 반영 여부 최종 승인

### 3.3 공동 수행

- [ ] Codex가 실행 로그와 raw artifact를 생성하고 사람이 대표 case를 검토
- [ ] 불일치 발견 시 annotation 수정 여부를 사람이 결정하고 Codex가 재집계
- [ ] provider·DB·브라우저 환경을 함께 확인한 뒤 E2E 결과를 확정

## 4. 6.5 단계 실행 게이트

### Gate A — 기준 데이터와 환경

- [x] fixture / Gold 파일과 SHA-256 고정
- [x] privacy-safe artifact 구조 확인
- [ ] 전체 annotation 승인
- [ ] 동일 code revision / model / 환경 기록

**통과 조건:** 사람 승인 annotation + 실행 환경 manifest가 존재해야 한다.

### Gate B — 추출 AI

- [x] 평가기 코드 존재
- [x] v3.0 corrected projection score 존재
- [ ] v3.1 30-case raw output 존재
- [ ] Atom / critical slot / lexical / expression / action-state 지표 산출
- [ ] fingerprint 및 repeat consistency 산출

**통과 조건:** v3.1 모든 case에 대해 Gold mapping 가능한 구조 JSON이 있어야 한다.

### Gate C — 점검 AI와 정정

- [ ] 발동 조건 fixture와 기대 상태 매핑
- [ ] `PASS / NEEDS_REVIEW / REEXTRACTION_REQUIRED` confusion matrix
- [ ] human review와 점검 AI 결과 비교
- [ ] correction resolution 및 case pass/fail

**통과 조건:** 정정·부정·완료 상태 fixture에서 의미 반전이 없어야 한다.

### Gate D — Fact 저장·lineage·projection

- [x] transaction / rollback / retry / idempotency / revision 회귀 테스트
- [ ] Atom→Relation→Signal→Fact→Statement lineage full report
- [ ] one-to-one, multi-value, aggregation loss 측정
- [ ] `BANK_INTERNAL`과 고객 visibility 격리 검사
- [ ] section projection accuracy 및 reload consistency

**통과 조건:** 모든 출력 Fact가 원자 근거와 visibility를 추적할 수 있어야 한다.

### Gate E — 안전성

- [ ] critical contradiction rate
- [ ] critical hallucination / unsupported claim rate
- [ ] privacy leak rate
- [ ] customer/bank role isolation

**Hard Gate 권고:** critical contradiction 0, critical hallucination 0, privacy leak 0.

### Gate F — 효율성과 E2E

- [x] v3.0 token baseline
- [ ] v3.1 token/call/latency 동일 fixture 3회
- [ ] P50 / P95 / MAX latency
- [ ] token per correct critical fact
- [ ] DB persistence / pipeline completion
- [ ] API / browser Case Room E2E

## 5. 실행 순서

1. 사람이 Gold annotation과 acceptance 기준을 승인한다.
2. Codex가 v3.1 provider replay를 동일 30 cases / 150 turns로 실행한다.
3. Codex가 raw structured output과 manifest를 저장한다.
4. 사람이 대표 critical case를 검토한다.
5. Codex가 통합 평가기를 실행해 v3.0/v3.1 점수를 산출한다.
6. Codex가 safety, token, latency, E2E 결과를 결합한다.
7. 사람이 최종 hard gate와 발표 문구를 승인한다.
8. Codex가 최종 보고서와 Notion 전달 payload를 갱신한다.

## 6. 실행 명령

현재 dry-run은 v3.1 artifact가 없으므로 `NOT RUN`을 반환한다.

```powershell
python "MVP_v3/docs/now_md/A_part/A파트 테스트 및 파이프라인 구조 정리/compare_v30_v31.py"
```

v3.1 raw output이 준비되면:

```powershell
python "MVP_v3/docs/now_md/A_part/A파트 테스트 및 파이프라인 구조 정리/compare_v30_v31.py" `
  --v31-output path/to/v3_1_structured_output.json
```

생성 위치:

- `run_comparison/comparison_metrics.json`
- `run_comparison/comparison_report.md`

## 7. 최종 완료 조건

- [ ] v3.1 30-case 전체 점수와 v3.0 동일 기준 점수 확보
- [ ] macro / critical / correction / lineage / projection 지표 확보
- [ ] hard gate 3종 통과 여부 확정
- [ ] token·calls·latency·token-per-correct-critical-fact 확보
- [ ] DB/API/browser E2E evidence 확보
- [ ] 대표 case human review 승인
- [ ] 최종 보고서와 Notion payload 갱신

위 조건을 모두 충족하기 전까지 종합 보고서는 `DRAFT`로 유지한다.

## 9. 2026-09-17 Codex verification log

- [x] `replay_benchmark/evaluator.py validate` 재실행: 30 cases / 270 atomic facts / 20 prompts / 10 E2E cases
- [x] 통합 비교기 dry-run 재실행: v3.0 `READY`, v3.1 `NOT_RUN`, hard gates `NOT_RUN`
- [x] 기존 sample `developer-structure.json` privacy scan 재실행: `PASS`, issues 0
- [x] 중복 6.5 실행 체크리스트 제거 및 본 문서를 단일 실행 기준으로 지정

### 지금 사람이 해야 하는 일

1. 공식 Gold annotation과 critical fixture의 정답성을 승인한다.
2. v3.1 replay에 사용할 commit·model·환경을 승인한다.
3. 대표 critical case의 의미 보존과 문장 자연스러움을 검토한다.
4. hard gate acceptance 기준을 승인한다.

사람 승인 전에는 Codex가 v3.1 점수나 `FINAL` 판정을 확정하지 않는다.

### AI-assisted review and fixture finding

- [x] Actual benchmark turn text verified: `FACT-01 == FACT-02 == FACT-03`
- [x] AI-assisted design review artifact recorded in `fixtures/human_review/REVIEW_DECISIONS_AI_ASSISTED.json`
- [x] Review queue recorded in `fixtures/human_review/review_queue.json`
- [x] Gold policy recorded in `fixtures/official_gold/FACT_CONTEXT_GOLD_README.md`
- [x] Human review guide corrected so FACT-02/03 are not misrepresented as distinct scenarios
- [ ] Human sign-off remains pending; AI-assisted review is not `HUMAN_CONFIRMED`

### 승인 반영

- [x] 사용자 승인: 공식 Gold annotation은 정답 기준으로 사용한다. (2026-09-17)
- [x] 사용자 승인: v3.1 replay commit·model·환경을 승인하고 실행을 진행한다. (2026-09-17)
- [ ] 실제 선택된 commit·model·환경값을 replay manifest에 기록
- [ ] 대표 critical case 사람 검토: [HUMAN_REVIEW_GUIDE.md](fixtures/human_review/HUMAN_REVIEW_GUIDE.md)
- [ ] safety hard gate 사람 검토: 같은 안내서의 `Critical contradiction / hallucination / privacy leak` 기준

## 10. v3.0 추가 측정 판단

v3.0의 핵심 corrected-Gold 점수와 token baseline은 이미 재사용 가능한 상태다. v3.0 전체를 처음부터 다시 실행할 필요는 없다.

다만 v3.1과 동일한 비교표를 완성하려면 다음 두 항목은 추가로 산출해야 한다.

- [x] `UNIQUE_SEQUENCE_WEIGHTED`: 중복 case 30건을 unique turn sequence 기준으로 재가중 — 2 sequences 중 1개 scored, 1개 `NOT_APPLICABLE`
- [ ] latency P50 / P95 / MAX: v3.1과 동일 provider·model·환경에서 v3.0 재실행

기존 `replay_benchmark/results/v3_0_live_20260916/latency.json`은 `NOT RUN`이고,
`hard_gates.json`은 DB/live-chat 미실행을 명시한 partial replay다. 따라서 historical
contradiction/hallucination 수치를 공식 hard gate 결과로 사용하지 않는다.

v3.0에서 추가로 다시 실행할 필요가 없는 항목:

산출물: `run_comparison/v30_unique_sequence_metrics.json`  
실행 코드: `measure_v30_unique_sequence.py`

- corrected-Gold comparable Recall / Precision / F1
- 7개 기능 × 3회 token usage baseline
- 공식 commit·dataset·Gold hash 확인

## 8. 관련 문서의 역할

- `A_6_5_MASTER_CHECKLIST.md`: **현재 문서 — 단일 실행 기준**
- `A_6_5_TEST_AND_PIPELINE_DESIGN.md`: 6.5단계 설계·평가 계약
- `A_IMPLEMENTATION_CHECKLIST.md`: 1~10단계 구현 체크리스트·이력(6.5 항목 포함)
- `A_6_5_FINAL_A_PART_COMPREHENSIVE_REPORT.md`: 결과 보고서 초안
- `A_PART_V3_0_V3_1_COMPARISON.md`: 비교 지표·해석 기준
- `A_HIGH_FIDELITY_SEMANTIC_CONTEXT_DESIGN.md`: v3.1 설계·계약 기준

기존 문서의 체크박스와 이 문서의 상태가 다르면, 실행 artifact가 있는지 확인한 뒤 이 마스터 체크리스트를 우선 갱신한다.
