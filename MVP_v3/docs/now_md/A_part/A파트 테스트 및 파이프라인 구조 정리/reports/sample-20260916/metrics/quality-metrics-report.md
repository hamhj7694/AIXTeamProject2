# A파트 6.5 품질 지표 보고서

평가 상태: `PENDING_HUMAN_ANNOTATION`  
Fixture: `VP-18`  
생성 시각: `2026-09-16T13:39:08.136502+00:00`

## 지표 요약

| 평가 대상 | 예측 수 | 정답 수 | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| event_decomposition | 5 | 0 | - | - | - |
| semantic_atom | 9 | 0 | - | - | - |
| critical_slot | 28 | 0 | - | - | - |
| observed_lexical_code | 0 | 0 | - | - | - |

## 해석

- `PENDING_HUMAN_ANNOTATION`이면 정답 라벨이 없어 점수를 계산하지 않은 상태입니다.
- 정답 없이도 Event-Atom turn coverage와 Relation/Signal lineage 같은 구조 지표는 확인할 수 있습니다.
- 정답 annotation을 확정한 뒤 같은 명령을 다시 실행해야 실제 Precision·Recall·F1이 생성됩니다.
- 이 자료는 내부 평가용이며 은행 직원용 웹 화면에 노출하지 않습니다.
- 원문과 민감 literal은 평가 결과에 저장하지 않습니다.

## 구조 지표

| 지표 | 값 |
|---|---:|
| Event→Atom turn coverage | 1.0 |
| Relation lineage rate | 1.0 |
| Context Signal lineage rate | 1.0 |
| Privacy status | `PASS` |
