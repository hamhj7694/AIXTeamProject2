# eom 담당 작업 매핑

## 역할

eom은 **AI 모델·AI API 제공자**다. WindowAI, LLM, RAG, STT 등 AI 기능을 모델 Adapter부터 내부 API의 구조화된 응답까지 책임진다.

## 소유 영역

```text
02_workspace/backend/ai_api/**
02_workspace/backend/contracts/ai_internal/**
02_workspace/backend/ai_api/models/**
AI Fixture·Prompt·평가 데이터·Contract Test
```

## 핵심 책임

- AI 내부 Request/Response Schema와 Example의 최종 편집
- WindowAI·Full Context LLM·Feature Extractor·Risk Fusion
- Report·Case Support·Knowledge RAG·Voice AI의 단계적 구현
- Model version, artifact hash, source/evidence, confidence 반환
- Timeout·부분 실패·Fallback을 포함한 AI API 오류 정책
- lee가 실제 AI 없이도 통합할 수 있는 결정론적 Fixture 제공
- AI API 단위 테스트·품질 평가·소비자 Contract Test 지원

## 담당 Task

| Task ID | 작업 | 산출물 | Reviewer |
|---|---|---|---|
| CT-02 | Diagnosis AI Contract | 내부 Schema·Example·오류 정책 | lee |
| AI-01~04 | 최초 진단 AI | LLM·WindowAI·Feature·Risk/Fusion | lee |
| AAPI-10 | Diagnosis AI API | 내부 Endpoint·Fixture·Contract Test | lee |
| AI-05/16 | Case Report AI | Initialize·Section Patch·FINAL | lee |
| AI-06~08 | Case Support AI | 질문·검증 계획·비정형 답변 구조화 | lee |
| AI-09~11 | Voice Intelligence | STT·Delta·Summary | lee |
| AI-12~15 | Knowledge AI | Verification·Response·Recovery·Institution RAG | lee |
| AAPI-20/21/30 | 후속 AI API | Report·Case Support·Knowledge Endpoint | lee |

## 수정하지 않을 영역

- `02_workspace/frontend/**`
- `02_workspace/backend/general_api/**`
- `02_workspace/backend/contracts/public_api/**`
- `02_workspace/backend/migrations/**`
- lee·ham의 개인 작업 문서

AI 결과 저장 방식이나 공개 화면 변경이 필요하면 lee에게 Contract 변경을 요청한다. 긴급 수정이라도 소유 영역을 넘어 직접 구현하지 않는다.

## 기존 작업 인계

eom이 기존 Vertical Slice에서 작성한 Frontend, General API, Migration 코드는 삭제하거나 되돌리지 않는다. 해당 코드는 `HANDOFF-01`을 통해 lee에게 소유권만 인계하며, 이후 수정은 lee가 담당한다.

## 권장 브랜치

```text
eom/ai-diagnosis
eom/ai-report
eom/ai-case-support
eom/ai-knowledge-rag
eom/ai-voice
```
