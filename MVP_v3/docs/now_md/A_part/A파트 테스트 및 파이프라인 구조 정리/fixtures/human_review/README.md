# 6.5단계 사람 검토용 Fixture 안내

이 폴더는 코덱스 1차 검토 결과를 사람이 확인하기 위한 검토 공간이다.

## 확인 순서

1. [v3.0 원본 benchmark](../../../../../../replay_benchmark/fact_context_cases.json)에서 `FACT-01`, `FACT-02`, `FACT-03`을 검색한다.
2. 해당 Case의 `turns`에서 원문을 확인한다.
3. `../official_gold/`의 공식 Gold 3개 중 해당 평가 목적에 맞는 파일을 연다.
4. `FACT_CONTEXT_CANONICAL_HUMAN_GOLD_v1.json`을 최종 사람 기준으로 우선한다.
5. `FACT_CONTEXT_GOLD_v3_1_HIGH_FIDELITY.json`에서 Atom·Relation·Context Signal을 확인한다.
6. `FACT_CONTEXT_GOLD_v3_0_CORRECTED.json`은 v3.0 비교 기준으로 확인한다.

원문은 이 폴더에 복사하지 않는다. 원문은 benchmark 파일에서만 확인하고,
검토 결과에는 구조화된 코드·상태·짧은 메모만 남긴다. 이전 partial gold나 review queue는 사용하지 않는다.

## 상태값

```text
V3_0_IMPORTED_GOLD  v3.0 기준선에서 가져온 정답
CODEX_PROVISIONAL   코덱스 1차 검토 대기/제안
HUMAN_CONFIRMED     사람이 확인한 공식 정답
NEEDS_REVIEW        의미가 불명확하거나 수정이 필요한 항목
```

## v3.1 신규 항목

다음은 v3.0 gold에 없으므로 v3.1 분석 결과가 생성된 뒤 별도 검토한다.

- `observed_lexical_codes`
- `expression_features`
- `relation_keys`
- `context_signal_keys`
