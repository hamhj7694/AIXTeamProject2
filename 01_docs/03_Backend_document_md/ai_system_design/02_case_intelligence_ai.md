# Case Intelligence AI 설계

## 1. 역할

진단, 위험 맥락, 비정형 답변 구조화, 후속 질문, 은행 Copilot을 하나의 AI Service 경계로 묶는다. 내부 모델 호출은 나뉠 수 있지만 독립 자율 Agent로 분리하지 않는다.

## 2. 기능

| 기능 | 입력 | 출력 |
|---|---|---|
| Full Text Analysis | 전체 통화 | 사건 유형, 주장, 요약, evidence |
| Window Analysis | 분할 Segment | 구간별 위험신호·text span |
| Feature Extraction | 전체/Segment 결과 | 표준 Context Feature |
| Risk Prediction | Feature | risk level·score·reason |
| Case Structuring | 비정형 답변 + 현재 필드 | Field Patch·conflict·evidence |
| Question Planning | 미확인 필드·Case State | P0/P1/P2 질문 후보·Options |
| Bank Copilot | 담당자 질문 + Case Projection | 근거 기반 지원 응답 |

## 3. 공통 Feature

```text
impersonation, authority, fear, urgency, isolation,
money_request, transfer_request, amount,
credential_exposure, privacy_exposure,
remote_control, verification_blocking
```

## 4. 질문 정책

- P0는 표준 질문 Registry에서 선택하며 자유 생성하지 않는다.
- P1/P2는 Draft로만 반환하고 담당자 승인 후 전송한다.
- 질문과 선택지를 별도 Entity로 반환한다.
- Bank Copilot은 고객에게 직접 메시지를 보내지 않는다.

## 5. API 연결

```text
POST /ai/analyze/text
POST /ai/analyze/windows
POST /ai/features/extract
POST /ai/risk/predict
POST /ai/case/structure
POST /ai/questions/next
```

Bank Copilot 전용 Endpoint는 실제 UX가 확정될 때 추가하며, MVP에서는 `/ai/questions/next`와 Case Structure 결과를 우선 사용한다.

## 6. 출력 필수값

```text
case_id
schema_version
result
evidence[]
confidence
warnings[]
```

Segment 결과에는 `segment_id` 또는 위치 정보를 포함한다.

## 7. 평가

- 정상 통화·정상 금융 상담·보이스피싱 분류
- Feature Precision/Recall
- 금액·기관·송금상태 사실 보존
- 근거 없는 사실 생성 비율
- 민감 질문 생성 여부
- P0 표준질문 준수율
- 평균·P95 Latency와 호출 비용

## 8. 완료조건

- [ ] 각 기능 Request/Response Schema 확정
- [ ] Full/Window 병렬 실행 가능
- [ ] Feature/Risk 평가 데이터셋 구축
- [ ] Structuring Conflict 처리
- [ ] Question Policy Guardrail 테스트
- [ ] Bank Copilot 근거 없는 확정 판단 차단
