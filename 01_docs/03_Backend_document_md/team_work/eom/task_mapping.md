# eom 담당 작업 매핑

## 역할

`/` 텍스트 입력부터 WindowAI·Diagnosis LLM 병렬 분석, Backend Case 생성, Frontend 상세 이동까지 최초 진단 Vertical Slice 전체를 소유한다.

## 소유 영역

```text
Frontend 최초 진단·Case API Client
일반 Backend analyze/core
AI Backend diagnosis/WindowAI
Diagnosis Contract와 Fusion
```

## 담당 Task

| Task ID | 작업 | 산출물 | 선행 | Reviewer |
|---|---|---|---|---|
| CT-01 | Public Analyze Contract | `/api/cases/analyze` Schema | 없음 | lee |
| CT-02 | Diagnosis AI Contract | ML/LLM Request·Response | 없음 | lee |
| BE-00 | Backend Skeleton | Server, Error, AI Client Interface | CT-01/02 | lee |
| DB-01 | Core Case Schema | case/input/segment/feature Migration | CT-01 | lee |
| FE-01 | Root API 연결 | API Client, Loading/Error, Navigate | CT-01 | lee |
| AI-01 | Diagnosis LLM | 전체 맥락 구조화 | CT-02 | lee |
| AI-02 | WindowAI | Segment 위험 분석 | CT-02 | lee |
| AI-03/04 | Feature·Risk Fusion | 표준 Feature, Risk 규칙 | AI-01/02 | lee |
| AAPI-10 | Diagnosis AI API | analyze text/windows/features/risk | AI-01~04 | lee |
| BE-01 | Case Analyze API | 병렬 호출·Fusion·저장 | BE-00, AAPI-10 | lee |
| INT-01 | 최초 진단 E2E | `/` → Case → 상세 이동 | FE-01, BE-01 | lee |

## 수정하지 않을 영역

- `ai_backend/report/**`
- `ai_backend/case_support/**`
- `ai_backend/knowledge/**`
- lee의 작업 문서
- ham 합류 후 소유가 확정된 Realtime/Voice/Verification 모듈

## 권장 브랜치

```text
eom/contract-case-analyze
eom/be-case-analyze
eom/ai-diagnosis
eom/fe-case-analyze
```

Contract PR을 먼저 병합하고 구현 Task는 작은 PR로 분리한다.
