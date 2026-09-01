# AI API

General API의 내부 요청을 받아 ML·LLM·RAG·음성 분석을 수행하고 구조화된 결과를 반환한다. 서비스 DB의 상태 변경은 담당하지 않는다.

```text
app/
├─ core/          # 모델 설정, 공통 오류·관측 처리
├─ domains/       # AI 기능별 구현
└─ clients/       # 외부 LLM, vector store, STT client
tests/            # 모델 adapter·API 계약 테스트
```

