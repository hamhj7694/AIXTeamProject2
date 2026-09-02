# AI Internal Contracts

## Current Diagnosis contract

현재 실행되는 Diagnosis 내부 Contract의 기준은
`contracts/diagnosis.py`의 Pydantic 모델이다.

- Request: `AnalyzeTextRequest`
- Response: `DiagnosisResult`
- Runtime JSON Schema: `DiagnosisResult.model_json_schema()`
- Runtime fixture: `fixtures/diagnosis.normal.v1.json`,
  `fixtures/diagnosis.high.v1.json`
- Validation test: `ai_api/tests/test_diagnosis_internal_contract.py`

정적 JSON Schema를 별도로 복제하지 않는다. Pydantic이 생성하는 JSON Schema를
기준으로 사용해 Runtime DTO와 복사본이 어긋나는 것을 방지한다.

## Future Report draft

`report_initialize_request.schema.json`과
`report_initialize_response.schema.json`은 B-4 Report AI를 위한
`FUTURE_DRAFT_PENDING_CASE_DTO`다. 현재 AI API endpoint, Pydantic DTO,
General API 호출 경로에는 연결되지 않았다.

따라서 이 Draft의 `MEDIUM` risk, feature 배열, `exposure_status` section은
현재 Diagnosis Runtime의 `RiskLevel`, `features`, `InitialReport`와 동일한
Contract가 아니다. Runtime validation 대상으로 해석하지 않는다.
