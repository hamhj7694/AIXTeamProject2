# AI 재사용 지도 · P0-002

2026-09-06 read-only 조사. 아래 원본 경로는 provenance이며 runtime 참조가 아니다.
공통 원본 root: `MVP_v3/backend/`. 원본 서비스를 시작하거나 실제 env를 읽지 않았다.
모든 행은 조사 완료. **P0-006에서 ML 모델/adapter만 물리 이식하여 실제 load/inference를 검증 완료**했다. 나머지 AI 기능은 이식/실호출 미완료다.

| 기능 / 원본 endpoint | 원본 module / 계약 | 입력 → 출력 | 의존/비용/부작용 | V4 이식 계획 |
|---|---|---|---|---|
| ML / /ai/analyze/text, /ai/risk/predict | ai_api/app/domains/diagnosis/{model_adapter,features,constants,window_ai/service}.py; contracts/diagnosis.py | text → events → features → risk/threshold/label | joblib/pandas/numpy/sklearn 1.6.1; ML 무료, event 추출 LLM 비용; DB write 없음 | P2-001 backend/ai_api/app/domains/diagnosis, backend/models, backend/contracts; 외부 model override 차단 |
| Context feature | diagnosis/context_features.py | transient text → enum codes/turn/status | OpenAI structured output, 1 call/1800 output tokens; DB write 없음 | P2-002 원문 폐기 경계 뒤로 free-text 전달 금지 |
| Reconstruction | diagnosis/{service,extractor,full_context_llm/service}.py | signal payload + CaseContextFeatures → ContextResult | OpenAI; V3 service는 low-risk에도 context 추출 | P2-002 threshold gate 추가, feature-only adapter |
| Conversational / /ai/case-copilot/replies | case_support/copilot_service.py; contracts/ai_internal/case_copilot.py; contracts/user_text.py | role/prompt/facts/chat/progress → content/model_mode | AsyncOpenAI; assignee lookup 0 call; customer rate/concurrency budget; DB write 없음 | P5-001 V4 role/snapshot adapter, hardcoded 연락처를 official lookup으로 전환 |
| WorkCard / /ai/work-cards/generate | case_support/work_card_service.py + copilot errors; ai_internal/work_card.py | BANK_ACTION 등 + snapshot → typed proposal | OpenAI structured output; provider fallback 성공 오인 방지 필요; DB write 없음 | P3-002/P5-003 후보 1–3, source revision, accept/edit/reject 후 Task |
| Snapshot / /ai/case-support/snapshot | case_support/{case_snapshot_adapter,workflow,agents,agent_router}.py; ai_internal/{case_snapshot,mvp_workflow}.py | diagnosis/facts/questions/verifications → presentation | deterministic workflow; DB write 없음 | V4 snapshot만 전달, V3 actions/repository 이식 금지 |
| 질문/답변 | case_support/{question_service,question_prompt,answer_service,answer_prompt}.py | Brief + question context → candidates; answer → structured fields | 규칙 기반, 자동발송 없음; resolved/pending/answered 중복 제거 | P4-001 원격앱 P0 보강(현재 _QUESTION_SPECS에 없음) |
| Brief | case_support/{brief_service,brief_prompt,brief_update_service}.py | diagnosis/state → CaseBrief | 규칙 및 선택 LLM; DB write 없음 | P6-001 제한 trigger, 직원 확정값 보존 |
| Final / /ai/final-reports/generate | case_support/final_report_service.py; ai_internal/final_report.py | case/facts/verification/tasks → report | OpenAI structured output; DB write 없음 | P6-001 종료 snapshot/version 기반 단회 저장 |
| Case lexical RAG | general_api/app/domains/cases/case_retrieval.py | authorized CaseRecord + query → source text/score | TF-IDF Korean n-grams, LRU 32, 2000 records, top≤6; 외부 embedding/DB write 없음 | P5-002 알고리즘만 이식, V3 collection/repository는 제외 |
| Official Verification RAG | 별도 AI endpoint/corpus/vector config 미확인 | V3 verification create/update는 직원 기록 CRUD | 사건 lexical RAG와 공식지식 검색은 다름 | GAP-AI-001: 공식 출처/연락처 provenance 및 새 검증 계약 필요. Mock 대체 금지 |

## 모델 provenance
- 원본: ai_api/models/WINDOW_LOGISTIC_DASHBOARD_EXPERIMENTAL_SAMPLE_v1.pkl
- SHA-256: 662db2a9351dc4ca2c453776ae6f45750e465234cc9abcecc65b58a6b047c5fc
- 상태 EXPERIMENTAL_SAMPLE, scikit-learn 1.6.1. 운영 승인/성능 검증으로 표현하지 않는다.
- threshold/guardrail/feature order는 bundle에서 읽는다. 임의 변경 금지.
- 원본 model_adapter의 외부 WINDOW_MODEL_PATH 허용 및 V3 venv 오류문구는 이식 시 제거.

## 비용/미검증
- 원본 DiagnosisLlmBudget: 31 calls / 16000 tokens / 30 turns / 6000 chars. V4 전체 이벤트에 자동 적용 금지.
- V3 endpoint/계약/핵심 코드 확인 완료. V3 서비스 실행/호출 없음. V4 local ML 실제 추론 PASS; LLM/RAG 실호출 NOT_RUN; 유료 호출 0.
- GAP-AI-001 별도 공식 RAG 경로를 사용자에게 질의함. 독립 scaffold는 진행 가능.
- P0-006에서 모델/adapter preflight를 먼저 실제 이식하고 원본/목적지 hash manifest 기록. P2는 이를 재사용해 intake 연결 및 privacy fixtures 검증.
- 외부 AI에는 `[USER_SECRET_REQUIRED] OPENAI_API_KEY` 필요. 기존 env 접근 금지.

## P0-006 이식 결과 (Gate PASS)
- destination: backend/models/WINDOW_LOGISTIC_DASHBOARD_EXPERIMENTAL_SAMPLE_v1.pkl. 원본과 byte-identical SHA-256.
- adapter: backend/ai_api/app/domains/diagnosis/model_adapter.py. 원본을 실제 복사 후 V4 내부 경로/verified bytes/finite input 검증으로 보강.
- 보존: model_features 순서 23개, threshold 0.95, 원본 predict_proba/guardrail/label 계산.
- 제거: 외부 WINDOW_MODEL_PATH override, 원본 venv 오류문구. V4 밖 파일/import/service 의존 없음.
- 실제 합성 입력: zero → raw 29.0294333167 / final 20 / NORMAL; signal 91개 → 97.6003550809 / PHISHING.
- 실험용 모델의 동작 검증이며 실제 통화 정확도/품질 평가 결과가 아니다. Text feature extraction은 P2-001/002에서 연결.
- 증거: docs/evidence/model-port-manifest.json, model_preflight.json, phase0_backend_smoke.json.
