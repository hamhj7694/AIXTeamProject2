# 새 통화 분석 실행 검증 — 2026-09-05

## 실제 실행 결과

- 요청 ID: `smoke-3d611f13b0e0476dbc54d86c43e6f90f`
- 샘플: 화면에 제공되는 검찰 사칭 통화 샘플, 분석 POST 1회
- 경로: `5176/api/cases/analyze → 8100 → 8101/ai/analyze/text → MySQL`
- 결과: HTTP 201 / CASE_CREATED / VP-4, 후속 GET HTTP 200
- AI 단계: 이벤트·ML 약 12.56초, 독립 맥락 피처 약 2.27초, 요약 약 1.95초
- 저장: Case 및 하위 데이터·LIVE Report를 같은 트랜잭션으로 커밋, 약 62ms
- 조회 검증: Report 7개 섹션, 독립 맥락 피처 관찰 6개, 원문 필드 비어 있음
- extractor_model: gpt-4o-mini, extraction_method: LLM_INDEPENDENT, partial_failure: false

## 호출 및 저장 순서

1. 중복 요청 키가 있으면 기존 성공 결과 확인.
2. AI 분석과 구조화 피처 기반 요약 생성.
3. 새 Case ID 및 Report 객체 준비(이 단계는 DB 조회 기반 Report 생성이 아님).
4. DB 트랜잭션에서 cases → case_inputs → analysis_segments → context_features → case_reports → case_report_sections → case_events 순서로 INSERT.
5. COMMIT 후 201과 case_id 반환. 하위 저장 실패 시 ROLLBACK.
6. 프론트의 후속 조회가 실패해도 생성 완료 상태를 유지해 재분석을 유도하지 않음.

## 오류 및 추적

- 두 API에서 X-Request-ID를 공유하며 단계·상태·소요 시간·예외 유형을 기록.
- 추적 로그에 통화 원문·인증 키·예외 본문을 기록하지 않음.
- AI 실패와 저장 실패(CASE_SAVE_FAILED)를 구분.
- 기존 Case 조회의 CASE_NOT_FOUND는 404. 분석 POST에서 503 CASE_NOT_FOUND는 이번 실행에서 재현되지 않음.
- Case INSERT의 중복 키 충돌만 저장 최대 3회 재시도. 이미 완료한 AI 분석은 재호출하지 않음.
- 생성 로그: `.runtime-logs/general-20260905-112027.err.log`, `.runtime-logs/ai-20260905-112027.err.log`.

## 별도로 남은 사항

- 이전 Connection error의 정확한 원인은 당시 로그가 없어 확정 불가. 이번에는 외부 네트워크 접근이 가능한 새 서버 프로세스에서 성공함.
- 실제 ML 아티팩트는 EXPERIMENTAL_SAMPLE. 아래 후속 수정에서 실행 환경 버전 불일치는 해소함.
- 기존 Case 자동 질문 오류는 아래 후속 수정에서 해소함.
- context_revision 및 마지막 정상 사건 맥락 DB 저장은 별도 후속 작업.

## 후속 수정 — 자동 질문 및 ML 실행 환경

- 원인: 공통 후보 ID(q_transfer_status 등)를 전역 PK로 저장하여 다른 Case의 동일 유형 질문과 충돌.
- 수정: 저장 인스턴스에 UUID 발급. 같은 Case의 큐 추가·발송은 부모 Case 행 잠금으로 직렬화.
- 기존 질문과 답변 ID는 그대로 보존. VP-2/3/4에서 자동 질문 저장 및 첫 질문 발송 확인.
- 질문 저장 후 remote_control_app을 AI snapshot에 전달할 때 발생하던 422도 내부 TargetField enum 보완으로 수정.
- 프로젝트 .venv를 생성하고 requirements.txt 설치(scikit-learn 1.6.1). 백엔드 두 개를 해당 환경으로 재시작.
- 모델 로더의 임시 내부 속성 보정을 제거. 다른 sklearn 버전에서는 시작 단계에서 명확히 실패하도록 검증.
- 실제 MySQL의 격리된 테스트 DB에서 두 Case의 동일 후보 저장, 동일 Case 동시 추가, 동시 발송 검증 통과. 임시 DB는 테스트 종료 시 제거됨.
- 실제 모델 로딩·예측에서 버전 경고 없음. pip check 통과. 이 후속 점검에서 유료 AI 생성 요청은 실행하지 않음.
