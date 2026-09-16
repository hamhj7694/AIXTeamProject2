# AI Runtime 오류 계약 (Step 5)

작성일: 2026-09-15

## 호출 경로 Inventory

| 기능 | General 경로/Client | AI Service | Provider | 기본 timeout | 실패 시 canonical mutation |
|---|---|---|---|---:|---|
| Diagnosis/Event | `HttpDiagnosisAiClient.analyze` | `DiagnosisService`/extractor | OpenAI Responses | `AI_API_TIMEOUT_SECONDS` (120) / provider 20초 | 없음; Case 저장 중단 또는 실패 상태 |
| Context Fact extraction | `extract_context_facts` | `ContextFactExtractionService` | OpenAI Responses | 120초 / provider 20초 | Fact 자동 확정 금지 |
| Customer/Bank Copilot | `generate_case_copilot_reply` | `CaseCopilotService` | OpenAI Responses | 120초 / provider 20초 | AI message 저장 금지 |
| Work Card | `generate_work_card` | `CaseWorkCardService` | OpenAI Responses | 120초 / provider 20초 | Action/Task 자동 생성 금지 |
| Final Report | `generate_final_report` | `FinalCaseReportService` | OpenAI Responses | 120초 | 가짜 report/finalize 금지 |
| Case support snapshot | `build_case_support_snapshot` | deterministic adapter 또는 AI 내부 경로 | 내부/AI | 120초 | deterministic 결과를 AI 결과로 표시 금지 |

## 공통 오류 taxonomy

| Code | 의미 | Retryable | HTTP | 사용자 메시지 |
|---|---|---:|---:|---|
| `AI_PROVIDER_UNAVAILABLE` | provider 연결 실패/일시 장애 | 예 | 503 | AI 기능을 일시적으로 사용할 수 없습니다. |
| `AI_PROVIDER_TIMEOUT` | provider timeout | 예 | 504 또는 503 | 응답 시간이 초과되었습니다. |
| `AI_PROVIDER_RATE_LIMITED` | quota/rate limit | 조건부 | 429 | 잠시 후 다시 시도해 주세요. |
| `AI_PROVIDER_AUTH_ERROR` | API key 인증 실패 | 아니오 | 401 | AI 설정을 확인해야 합니다. |
| `AI_INVALID_RESPONSE` | JSON/schema/필수 필드 오류 | 아니오 | 502 | AI 응답을 처리하지 못했습니다. |
| `AI_CONTRACT_VIOLATION` | 내부 DTO/business validation 위반 | 아니오 | 422 | 결과를 저장하지 않았습니다. |
| `AI_SERVICE_UNAVAILABLE` | AI API 자체 장애 | 예 | 503 | AI 기능을 일시적으로 사용할 수 없습니다. |

기존 `OPENAI_*`·기능별 `AI_*_FAILED` 코드는 Frontend 호환을 위해 `legacy_code`로 보존할 수 있다. `detail`은 최소한 `code`, `message`, `retryable`을 포함한다.

## Retry·timeout 경계

- provider boundary 안에서만 bounded retry를 허용한다. 기본은 initial + 1회 이하이며, 사용자 POST 전체를 재실행하지 않는다.
- timeout, connection error, 429, 일부 5xx만 retry 대상이다.
- 인증 오류, 잘못된 요청, schema mismatch, business validation 오류는 retry하지 않는다.
- `/readiness`는 API key 설정 여부만 확인하고 실제 OpenAI 호출을 하지 않는다. `/health`는 프로세스 생존만 나타낸다.

## 기능별 fallback

| 기능 | 정책 | provider 실패 시 |
|---|---|---|
| Diagnosis | `NO_FAKE_FALLBACK` | 정상/NORMAL/NO_CASE로 바꾸지 않고 명시적 실패 |
| Context extraction | `NO_FAKE_FALLBACK` | Fact 생성·확정 없음 |
| Copilot | `NO_FAKE_FALLBACK` | AI message 저장 없음; 일반 채널은 계속 가능 |
| Work Card | `NO_FAKE_FALLBACK` | 가짜 추천/Action/Task 없음; 직원 수동 입력 허용 |
| Final Report | `NO_FAKE_FALLBACK` | report 저장·finalize 없음 |
| deterministic candidates | `SAFE_RULE_FALLBACK` | AI 추천으로 표시하지 않고 규칙 기반 후보로만 표시 |

## 로그·보안

로그에는 `request_id`, `case_id`(가능한 경우), `task_type`, model, service version, error code, retry count, latency를 남길 수 있다. API key, 원문, OTP, 전체 개인정보는 남기지 않는다.

## Step 6 전달 원칙

Message extraction은 provider 실패 시 `PENDING`/`FAILED`와 bounded retry를 사용하고, 검증된 evidence가 있을 때만 `PROPOSED` Fact를 생성한다. 이번 단계에서는 seed/extraction 계약이나 hierarchical feature를 변경하지 않는다.

## 상태

- External AI live call: **NOT RUN**
- DB migration: **NONE**
- Frontend change: **NOT REQUIRED**
- Commit/Push: **NONE**

