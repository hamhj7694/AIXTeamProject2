# AI API

General API의 내부 요청을 받아 ML·LLM·RAG·음성 분석을 수행하고 구조화된 결과를 반환한다. 서비스 DB의 상태 변경은 담당하지 않는다.

```text
app/
├─ core/          # 모델 설정, 공통 오류·관측 처리
├─ domains/       # AI 기능별 구현
└─ clients/       # 외부 LLM, vector store, STT client
tests/            # 모델 adapter·API 계약 테스트
```

## 현재 Diagnosis 실행

작업 디렉터리는 반드시 `MVP_v3/backend`로 둔다.

```powershell
python -m pip install -r requirements.txt
python -m uvicorn ai_api.app.main:app --port 8101 --reload
```

환경변수는 `MVP_v3/.env`에서 자동으로 읽는다. 별도의
`MVP_v3/backend/.env`를 만들거나 터미널마다 다시 입력할 필요가 없다.
실제 이벤트 추출은 루트 `.env`의 `OPENAI_API_KEY`를 설정해 실행한다.
목데이터 실행 모드는 지원하지 않는다. LLM은 이벤트와 원문 근거만 추출하며,
위험 점수와 판정은 승인된 Window Logistic artifact가 담당한다.

## Context V3 사실 추출

`/ai/context/facts/extract`는 `OPENAI_CONTEXT_MODEL`을 통한 실제 provider
호출만 허용한다. provider 키가 없거나 호출·응답 검증에 실패하면 503으로
실패하며, 규칙/정규식 기반 결과로 대체하지 않는다. 따라서 General API는
provider 응답이 확인된 제안만 Context 패널 저장 대상으로 전달한다.

### 패널 반영 경계

- 최초 사건 생성: provider 진단의 structured atoms/signals만 초기 Fact 후보로 투영한다.
- 일반 채팅·직원 내부 채팅·고객 질문 답변: 메시지를 provider-only Context extractor로 보내고, 그 응답만 Fact 후보로 저장한다.
- General API의 코드는 검증·중복 제거·근거 연결·안전한 표시만 담당하며, 원문에서 기관·역할·금액 등의 의미를 임의로 만들지 않는다.
- 담당자 직접 입력과 공식기관 확인 결과는 AI Fact가 아니라 각각 `STAFF_OBSERVATION`·`OFFICIAL_VERIFICATION` 근거로 구분한다.

