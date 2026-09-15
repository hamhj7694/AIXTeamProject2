# LLM Context Test — 여기서 시작하세요

이 폴더는 **이전 LLM pipeline의 수준을 보존하고, 앞으로 개선한 버전을 같은 기준으로 비교하기 위한 최소 테스트 묶음**이다.

```text
원문
→ LLM/Event Feature 추출
→ 숫자 Feature 및 Context code 생성
→ 위험·맥락 분석
→ 맥락 재구성
→ Case 저장 직전 구조
```

## 파일은 이것만 보면 된다

| 파일 | 역할 |
|---|---|
| `00_START_HERE.md` | 사람이 읽는 전체 설명 |
| `baseline_v1/dataset.json` | 변경하지 않는 합성 원문 30건과 Ground Truth |
| `baseline_v1/raw_results.json` | 2026-09-06 실제 pipeline 실행의 sample별 원본 결과 |
| `baseline_v1/metrics.json` | 이전 버전의 핵심 기준 점수 |
| `baseline_v1/feature_inventory.csv` | 당시 Feature 이름·의미·형식·소비 위치 |
| `baseline_v1/manifest.json` | 실행 시각, dataset/result/model hash |
| `evaluate.py` | 기존 결과 재집계 및 개선 버전 비교 실행기 |
| `test_evaluate.py` | 기준선과 계산 계약이 변하지 않는지 확인 |

## 이전 버전 기준 점수

| 영역 | 지표 | Baseline v1 |
|---|---|---:|
| LLM Context Feature 추출 | Recall | 0.4145 |
| LLM Context Feature 추출 | Precision | 0.4638 |
| 숫자 Feature | Recall | 0.2359 |
| 숫자 Feature | Precision | 0.4495 |
| Entity | Recall | 0.7667 |
| 금액 | Recall | 0.9667 |
| 맥락 재구성 | Critical Fact Recall | 0.3137 |
| 맥락 재구성 | Fact Precision | 0.3475 |
| 맥락 재구성 | Semantic Similarity | 0.4679 |
| 안전성 | Contradiction | 7건 |
| 안전성 | Hallucination | 76건 |

모순과 환각이 0이 아니므로 baseline v1의 hard gate 결과는 `FAIL`이다.

## 꼭 비교해야 하는 항목

### 1. 피처 추출 품질

- `context_feature_recall`: 기대한 Context code 중 실제 추출 비율
- `context_feature_precision`: 추출한 Context code 중 올바른 비율
- `numeric_feature_recall/precision`: 위험 분석용 숫자 Feature의 누락·과잉
- `entity_recall/precision`: 기관, 사람, 연락처 등 주체 보존
- `amount_recall/precision/exact_match`: 요구·실제 금액 보존
- 원문 evidence turn/span 연결률: baseline v1에는 완전한 점수가 없어 개선 버전에 추가 필요
- 상태·극성 정확도: 요구/수행/거절/완료 구분. baseline v1에는 독립 지표가 없어 개선 버전에 추가 필요

### 2. 피처 구조 기록

- 숫자 Feature 후보 개수: 152개
- ML selected Feature 개수: 23개
- sample 간 후보 schema 일치율
- ML 입력 이름과 순서 일치율
- Feature별 이름, 한국어 의미, 값 형식, extractor/ML/LLM 사용 여부
- 관찰된 Context code 목록과 sample별 활성 code 개수

세부 목록은 `baseline_v1/feature_inventory.csv`, 실행 가능한 구조 profile은 `evaluate.py` 출력의 `feature_profile.json`에 기록된다.

### 3. 맥락 재구성 품질

- `critical_fact_recall`: 원문의 핵심 사실을 얼마나 보존했는가
- `fact_precision`: 재구성 문장 중 원문 근거가 있는 사실의 비율
- `contradiction_count`: 원문과 반대되는 진술
- `hallucination_count`: 원문에 없는 신호·사실·금액
- `semantic_similarity`: 원문/기준 요약과 생성 맥락의 의미 유사도

Semantic Similarity는 보조 지표다. “송금을 요구받음”을 “송금을 완료함”으로 바꾸면 문장이 유사해도 실패다.

### 4. Case화 및 운영 기록

- `case_projection_success_rate`: 저장 직전 Case projection 생성 성공률
- `no_database_write_rate`: 평가 중 DB write가 없었는지
- sample 성공률
- 평균/P50/P95 latency
- dataset, raw result, model artifact, prompt/evaluator, Git commit hash

baseline v1은 Case 저장 직전 projection까지 평가했으며 실제 DB에는 쓰지 않았다. 최신 Canonical Fact, conflict/supersede, Context V3 7개 Section 전체를 평가한 결과는 아니므로 개선 dataset에서 별도 항목을 추가해야 한다.

## 추가로 필요한 핵심 지표

향후 개선 버전에는 다음을 우선 추가한다.

1. `evidence_grounding_rate`: 추출 Fact가 실제 원문 근거를 가리키는 비율
2. `status_or_polarity_accuracy`: 요구·거절·부분 수행·완료·정정 구분
3. `case_creation_contract_accuracy`: 위험 조건과 Case 생성 여부 일치
4. `normal_false_positive_rate`: 정상 상담을 위험 Case로 오인하는 비율
5. `repeat_consistency`: 같은 입력을 여러 번 실행했을 때 결과 안정성
6. `privacy_leak_count`: 원문 또는 비공개 정보가 저장·고객 공개 경계를 넘은 횟수
7. `latency/token/cost`: 품질 개선으로 운영 비용이 과도하게 증가하지 않는지

## 재실행

저장소 루트에서 기준선 계약을 확인한다.

```powershell
MVP_v3\.venv\Scripts\python.exe -m pytest tests/context_test/test_evaluate.py -q
```

기준선 raw result를 다시 집계한다. 출력 폴더는 기존 경로를 덮어쓰지 않도록 새 이름을 사용한다.

```powershell
MVP_v3\.venv\Scripts\python.exe tests/context_test/evaluate.py `
  --input tests/context_test/baseline_v1/raw_results.json `
  --output tests/context_test/run_baseline_check
```

나중에 동일 형식의 개선 버전 raw result가 생기면 다음처럼 비교한다.

```powershell
MVP_v3\.venv\Scripts\python.exe tests/context_test/evaluate.py `
  --input <candidate_raw_results.json> `
  --output tests/context_test/run_<candidate_version> `
  --compare-to tests/context_test/baseline_v1/metrics.json
```

같은 dataset과 같은 metric 정의를 사용한 경우에만 delta를 성능 개선으로 해석한다.

## 안전과 불변 조건

- `baseline_v1` 파일은 수정하거나 덮어쓰지 않는다.
- 실제 고객 원문, 개인정보, API key, `.env`, DB dump를 넣지 않는다.
- baseline 재집계는 외부 LLM과 DB를 사용하지 않는다.
- 개선 live 실행은 별도 승인 후 수행한다.

