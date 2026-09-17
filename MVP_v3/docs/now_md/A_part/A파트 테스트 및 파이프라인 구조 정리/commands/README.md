# Commands

fixture 실행, JSON export, 지표 산출, privacy scan, E2E 검증 명령과 실행 환경을 기록한다.

## 현재 제공 명령

백엔드에서 LLM 분석을 새로 실행하는 경우:

```powershell
..\.venv\Scripts\python.exe -m scripts.export_context_quality_report `
  --input <transient-fixture.txt> `
  --output-dir "..\docs\now_md\A_part\A파트 테스트 및 파이프라인 구조 정리\reports\YYYYMMDD"
```

기존 `DiagnosisResult` JSON을 재분석 없이 보고서화하는 경우:

```powershell
..\.venv\Scripts\python.exe -m scripts.export_context_quality_report `
  --diagnosis-json <diagnosis-result.json> `
  --output-dir "..\docs\now_md\A_part\A파트 테스트 및 파이프라인 구조 정리\reports\YYYYMMDD"
```

두 명령 모두 `developer-structure.json`과 `human-review-report.md`를 생성한다.
운영 DB에 직접 쓰지 않으며, 원문·민감 literal을 결과에 저장하지 않는다.

정답 annotation을 확정한 뒤 Precision·Recall·F1을 산출한다:

```powershell
..\.venv\Scripts\python.exe -m scripts.evaluate_6_5_metrics `
  --predicted <developer-structure.json> `
  --gold <gold-annotation.json> `
  --output-dir "..\docs\now_md\A_part\A파트 테스트 및 파이프라인 구조 정리\reports\YYYYMMDD-metrics"
```

annotation이 아직 비어 있으면 결과 상태는 `PENDING_HUMAN_ANNOTATION`이며 점수를 만들지 않는다.

공식 Gold 정답지는 `fixtures\official_gold\`에 보관한다. 이전 partial gold 생성기는
호환성 테스트용으로만 남겨두며, 새 평가의 Gold 입력으로 사용하지 않는다.

v3.0 benchmark의 Case·atomic fact·패널 섹션 분포 요약:

```powershell
..\.venv\Scripts\python.exe -m scripts.summarize_6_5_benchmark `
  --input ..\..\replay_benchmark\fact_context_cases.json `
  --output-dir "..\docs\now_md\A_part\A파트 테스트 및 파이프라인 구조 정리\reports\v3_0-benchmark-summary"
```

산출물 privacy scan:

```powershell
..\.venv\Scripts\python.exe -m scripts.validate_6_5_artifact <developer-structure.json>
```

두 실행 결과 재현성 비교:

```powershell
..\.venv\Scripts\python.exe -m scripts.compare_6_5_reports `
  <first-developer-structure.json> <second-developer-structure.json> `
  --output <reproducibility-diff.json>
```

v3.0 baseline과 v3.1 현재 구조 비교:

```powershell
..\.venv\Scripts\python.exe -m scripts.build_6_5_baseline_comparison `
  --baseline ..\..\replay_benchmark\results\v3_0_core_metrics_20260916\core_metrics.json `
  --current <developer-structure.json> `
  --output-dir "..\docs\now_md\A_part\A파트 테스트 및 파이프라인 구조 정리\reports\YYYYMMDD-baseline"
```
