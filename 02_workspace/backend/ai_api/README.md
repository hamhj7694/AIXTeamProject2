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

작업 디렉터리는 반드시 `02_workspace/backend`로 둔다.

```powershell
python -m pip install -r requirements.txt
$env:DIAGNOSIS_EXTRACTOR_MODE = "fixture"  # API key 없는 로컬 검증 전용
python -m uvicorn ai_api.app.main:app --port 8001 --reload
```

실제 이벤트 추출은 `.env` 또는 터미널 환경변수에 `OPENAI_API_KEY`를 설정하고
`DIAGNOSIS_EXTRACTOR_MODE=openai`로 실행한다. LLM은 이벤트와 원문 근거만 추출하며,
위험 점수와 판정은 승인된 Window Logistic artifact가 담당한다.

