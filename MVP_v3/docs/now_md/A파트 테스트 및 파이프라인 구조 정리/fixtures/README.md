# Fixtures

공식 Gold 정답지와 privacy-safe 평가 fixture를 보관한다.
통화 원문이나 민감 literal은 저장하지 않는다.

## 공식 Gold 정답지

현재 공식 정답지는 `official_gold/` 안의 다음 3개 파일뿐이다.

- `FACT_CONTEXT_GOLD_v3_0_CORRECTED.json`
- `FACT_CONTEXT_GOLD_v3_1_HIGH_FIDELITY.json`
- `FACT_CONTEXT_CANONICAL_HUMAN_GOLD_v1.json`

이전 `vp18-gold.annotation.template.json`, `v3_0_imported/`, 기존 human review 정답 파일은 제거했다.
v3.0 benchmark 원문은 정답지가 아니라 source reference이므로 `replay_benchmark/fact_context_cases.json`에서 확인한다.
