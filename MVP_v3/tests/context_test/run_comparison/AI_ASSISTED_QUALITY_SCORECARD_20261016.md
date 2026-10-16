# CSR A파트 6.5 보충 평가 — AI 초안 + 사용자 검수 정답 기준 (2026-10-16)

> **평가 구분: 탐색적·재현 가능한 내부 분석. 공식 동일 조건 개선율이 아님.**
>
> 이 보고서는 2026-09-16 VP-18 *단일 샘플* 보고서의 미산출 값에 임의의 점수를 채워 넣지 않고,
> **별도의 v3.1 30-Case 재실행 결과**를 AI 보조 라벨링 후 사용자가 검토·승인했다고 확인한
> canonical reference와 대조한 보충 점수표다. 검수 사실은 프로젝트 소유자의 확인을 별도 파일로 기록했으며, 독립 전문가의 검증을 주장하지 않는다.

## 1. 기존 VP-18 보고서의 0과 빈칸 해석

- 원래 보고서는 Event 5건, Semantic Atom 9건, Critical Slot 28건을 **예측**했고,
  정답 라벨은 0건 **미등록**이었다. Precision / Recall / F1의 `-`는 **0점이 아니라 미산출**이다.
- 당시 Event→Atom turn coverage 1.0, Relation lineage rate 1.0,
  Context Signal lineage rate 1.0은 **참조 무결성 성격의 구조 지표**이지 의미 정확도가 아니다.
  Context Signal이 0개인 샘플에서 lineage rate 1.0은 빈 대상에 대한 기본 반환값이다.
- 기존 스크립트의 `privacy_status: PASS`는 하드코딩된 상태값이므로
  별도의 실질적인 개인정보 유출 테스트 합격 증거로 해석하지 않는다.
- VP-18의 실제 입력 원문과 독립적으로 확정된 6.5 Event/Atom/Slot gold는 확보하지 못했다.
  따라서 **원본 VP-18의 네 품질지표는 여전히 미산출**이다.

기존 파일(삭제 전 커밋 고정 링크):
[VP-18 quality-metrics-report.md](https://github.com/hamhj7694/AIXTeamProject2/blob/b297c2fa430d517908430e14e167d14c87ad8f53/MVP_v3/docs/now_md/A_part/A%ED%8C%8C%ED%8A%B8%20%ED%85%8C%EC%8A%A4%ED%8A%B8%20%EB%B0%8F%20%ED%8C%8C%EC%9D%B4%ED%94%84%EB%9D%BC%EC%9D%B8%20%EA%B5%AC%EC%A1%B0%20%EC%A0%95%EB%A6%AC/reports/sample-20260916/metrics/quality-metrics-report.md).

## 2. v3.0 과거 결과와 v3.1 신규 계산

평가 단위: Case 단위 5개의 정답 슬롯이 **긍정적으로 존재하는지** 여부.
- 범죄 연루 주장, 인증번호 제공 요구, 송금 요구/지시, 안전계좌 명분, 긴급성(IMMEDIATE)
- v3.1 예측 판정: 저장된 `structured_output.case_context_features`의 선언된 코드와
  `semantic_atoms`의 T4 `CLAIMED_SAFE_ACCOUNT` 목적지를 검사하는 규칙 기반 projection.
- v3.1 기준 정답: `FACT_CONTEXT_CANONICAL_REFERENCE_WITH_EVIDENCE_v1.json`(원본은 AI 보조 초안 메타데이터 유지),
  이후 사용자가 **직접 확인·승인했다고 밝힌 내역**을 [검수 확인 기록](HUMAN_REVIEW_ATTESTATION_20261016.json)에 별도 저장.
  본 보고서에서 **Human-Reviewed Gold**는 이 두 자료를 합쳐 지칭한다.
- 30 Case / 150 Turn이지만 **고유 5-Turn 대화 시퀀스는 2개뿐**이다.

| 지표 | v3.0 보정 Gold 과거 집계 | v3.1 신규 5-슬롯 탐색 집계 |
|---|---:|---:|
| Case 수 | 30 | 30 |
| 정답으로 존재하는 핵심 사실 | 100 | 100 |
| TP / FP / FN | 14 / 0 / 86 | **87 / 3 / 13** |
| Precision | 100.0% | **96.7%** |
| Recall | 14.0% | **87.0%** |
| F1 | 24.6% | **91.6%** |
| 성격 | 기존 v3.0 결과를 보정 Gold로 감사한 기록 | 실제 v3.1 Raw Replay + 사용자 검수 확인된 AI 보조 reference + 새 규칙 |
| 동일 평가기로 재실행했는가 | **아니오** | **아니오** |

**이 표에서 +73.0%p 개선 등 직접 비교 변화량은 산출하지 않는다.**
핵심 의미 키는 비슷하지만 서로 다른 버전의 구조화 output에서 각기 다른 판정 규칙을 사용했다.
또한 과거의 Critical Fact Recall 31.37% 기록과 이 표의 v3.0 14.0%는
정답셋·평가 기준이 다른 별개 결과이므로 혼동하지 않는다.

### v3.1 다섯 슬롯별 탐색 집계

| 핵심 사실 | TP | FP | FN | TN | Recall |
|---|---:|---:|---:|---:|---:|
| 범죄 연루 주장 | 20 | 0 | 0 | 10 | 100.0% |
| 인증번호 제공 요구 | 20 | 0 | 0 | 10 | 100.0% |
| 송금 요구·지시 | 7 | 3 | 13 | 7 | **35.0%** |
| 안전계좌 명분 | 20 | 0 | 0 | 10 | 100.0% |
| 긴급성 | 20 | 0 | 0 | 10 | 100.0% |
| **합계** | **87** | **3** | **13** | **47** | **87.0%** |

위 점수는 **해당 다섯 항목에 대한 존재 탐지만 측정**한다.
기관·역할의 실제 확인 여부, 송금 완료와 요구의 구분, 금액 근거, 부정·정정 상태,
원문 근거 정확도, Relation/Context Signal 정밀도 등은 이 평가에서 다루지 않았다.
그러므로 기존 6.5 `event_decomposition`·`semantic_atom`·`critical_slot`·
`observed_lexical_code`의 Precision/Recall/F1을 대신하지 않는다.

## 3. 실무상 관찰과 검증 필요 사항

- 가장 눈에 띄는 결손은 **송금 요구 누락 13/20**, 정상 시퀀스에서
  **송금 요구 오탐 3/10**이다. 해당 구조의 polarity / action_state를 재검토할 필요가 있다.
- v3.1 `risk_level`은 위험 시퀀스 20개 중 1개를 NORMAL로,
  정상 시퀀스 10개 중 4개를 HIGH로 기록했다. 이는 별도 위험도 판정 진단이며
  위 **사실 추출 점수와는 다른 평가 대상**이다.
- 정답 30건은 **AI가 초안을 작성했고, 프로젝트 소유자가 검토·승인했다고 확인했다.**
  GitHub에는 이전까지 FACT-01~03의 검수 기록만 존재했으므로, 사용자가 확인한 검수 사실을
  별도 [30건 검수 확인 기록](HUMAN_REVIEW_ATTESTATION_20261016.json)으로 보완했다.
  다만 이 기록은 **소유자 본인의 확인**이지, 독립 심사자가 매 건마다 서명한 감사 기록이 아니다.
  **AI 초안을 사람이 처음부터 직접 라벨링한 것으로 표현하지 않는다.**
- 동일 원문이 반복된 fixture이므로 평균·분산·일반화 성능의 근거로 부족하다.
  2개 고유 시퀀스 이상의 새 사례를 확보해야 한다.

## 4. 계산 재현 방법

원래의 30-Case raw 및 AI reference 파일은
[보관 커밋 b297c2f](https://github.com/hamhj7694/AIXTeamProject2/tree/b297c2fa430d517908430e14e167d14c87ad8f53)의
`MVP_v3/docs/now_md/A_part/A파트 테스트 및 파이프라인 구조 정리/` 아래에 있었다.
해당 폴더는 이후 `main`에서 제거됐으므로 이 새 문서는 **원본을 복구·덮어쓰지 않는다**.

아래 두 파일을 보관 커밋에서 로컬로 추출하여 입력으로 사용한다.

- **REPLAY**: `run_comparison/v3_1_live_ai_20260917_30case.json` (blob SHA `7d8fb779777995a6509c184760d9f751ff1998ad`)
- **REFERENCE**: `fixtures/official_gold/FACT_CONTEXT_CANONICAL_REFERENCE_WITH_EVIDENCE_v1.json` (blob SHA `02a5e63a9191db6f371eb7cfa88f01ecf7f4532e`)

추출한 파일 위치를 지정해서 실행:

```bash
python MVP_v3/tests/context_test/run_comparison/score_ai_assisted_reference.py \
  --replay /path/to/v3_1_live_ai_20260917_30case.json \
  --reference /path/to/FACT_CONTEXT_CANONICAL_REFERENCE_WITH_EVIDENCE_v1.json \
  --review-record MVP_v3/tests/context_test/run_comparison/HUMAN_REVIEW_ATTESTATION_20261016.json \
  --output /path/to/exploratory_5_slot_metrics.json
```

이 evaluator는 별도의 LLM 호출이나 API 비용이 필요 없다.
새 gold를 모델 자신의 output에서 추출하지 않고, **이미 존재하는 AI-assisted reference와
저장된 replay 출력**을 분리해 읽어 계산한다.

## 5. 후속 공식 검증을 위한 최소 조건

동일 30개뿐 아니라 신규·다양한 Case를 추가해 정답을 확인한 뒤,
v3.0과 v3.1을 **같은 입력·같은 Gold·같은 projection 및 scorer**로 재실행해야
실제 버전별 개선율을 말할 수 있다. VP-18의 네 원래 지표를 채우려면
독립적인 Event/Atom/Slot 레벨 annotation도 별도로 필요하다.
