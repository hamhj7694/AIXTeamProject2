# v3.0 Baseline · v3.1 A파트 비교 보고서

v3.0의 과거 성능 수치와 v3.1의 현재 구조 상태를 나란히 비교한 내부 자료입니다.
측정하지 않은 v3.1 수치는 0점으로 간주하지 않고 `PENDING_HUMAN_ANNOTATION`으로 표시합니다.

## 비교표

| 지표 | v3.0 Baseline | v3.1 현재 |
|---|---:|---:|
| Context Feature Recall | NOT RUN | PENDING_HUMAN_ANNOTATION |
| Risk Detection F1 | 66.7% | PENDING_HUMAN_ANNOTATION |
| Negation Accuracy | 100.0% | PENDING_HUMAN_ANNOTATION |
| Contradiction | 7 cases (historical baseline) | PENDING_HUMAN_ANNOTATION |
| Hallucination | 76 cases (historical baseline) | PENDING_HUMAN_ANNOTATION |

## v3.1 현재 구조 건수

| 구조 | 건수 |
|---|---:|
| events | 5 |
| semantic_atoms | 9 |
| semantic_relations | 2 |
| context_signals | 0 |

## 해석

- v3.0 수치는 비교 기준선이며 v3.1의 공식 점수가 아닙니다.
- v3.1 신규 Atom·Observed Term·Relation·Context Signal은 v3.0에 없으므로 별도 annotation이 필요합니다.
- v3.1 정확도 산출 후 같은 표의 `PENDING` 값을 실제 수치로 교체합니다.
