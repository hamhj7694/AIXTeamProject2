# 팀 작업 운영 안내

## 현재 역할

| 작업자 | 현재 역할 | 참여 상태 |
|---|---|---|
| eom | AI 모델·AI API 제공자 | ACTIVE |
| lee | Frontend·General API·DB 통합 담당자 | ACTIVE |
| ham | 현재 작업 범위에서 제외, 추후 재배정 | PAUSED |

## 책임 경계

```text
Frontend                         lee
    ↓ Public API Contract        lee 최종 편집
General API + DB                 lee
    ↓ AI Internal Contract       eom 최종 편집, lee 소비자 Review
AI API + Model/LLM/RAG/STT       eom
```

- eom은 모델만 만들고 넘기는 역할이 아니다. 모델 Adapter부터 구조화된 AI API 응답, Fixture, 평가·오류 처리까지 소유한다.
- lee는 단순 중계만 담당하지 않는다. Frontend 요청, General API Workflow, AI Client, DB 저장, 공개 응답과 E2E를 소유한다.
- Frontend는 AI API를 직접 호출하지 않는다.
- AI API는 서비스 DB를 직접 수정하지 않는다.
- ham에게는 현재 Task와 코드 소유권을 배정하지 않는다.

## 폴더 구조와 소유권

```text
02_workspace/
├─ frontend/**                                      lee
└─ backend/
   ├─ general_api/**                               lee
   ├─ ai_api/**                                    eom
   ├─ contracts/
   │  ├─ public_api/**                             lee
   │  └─ ai_internal/**                            eom
   ├─ migrations/**                                lee
   ├─ docker/**                                    변경 전 담당자 지정
   └─ requirements.txt                             변경 전 상대 Review
```

`contracts/diagnosis.py`처럼 양쪽 서비스가 함께 import하는 파일은 계약 종류에 따라 최종 편집자를 정한다. AI 내부 DTO는 eom, 공개 DTO는 lee가 최종 반영하며 상대방 Review 없이 호환성을 깨지 않는다.

## 충돌 방지 규칙

1. 전체 배정은 조정자만 `00_task_catalog.md`에서 수정한다.
2. 각 작업자는 자신의 `task_mapping.md`와 `todo.md`만 진행 기록용으로 수정한다.
3. eom은 `general_api`, `frontend`, `migrations`를 직접 수정하지 않는다.
4. lee는 `ai_api`의 모델·Prompt·RAG 구현을 직접 수정하지 않는다.
5. 계약 변경은 Example JSON과 Contract Test를 먼저 수정한 뒤 구현한다.
6. 공통 Root 설정·Docker·Dependency 파일은 변경 전에 담당자와 Reviewer를 정한다.
7. 한 PR은 가능한 한 하나의 Task ID와 하나의 소유 영역만 포함한다.

## 병렬 작업 방식

```text
1. Public Contract(lee) + AI Internal Contract(eom) 합의
                         ↓
2A. eom: 실제 AI API 구현·평가
2B. lee: AI Fixture/Mock Client로 Frontend↔General API↔DB 구현
                         ↓
3. lee가 Fixture Client를 실제 AI API Client로 교체
                         ↓
4. eom은 AI Contract Test, lee는 공개 API·E2E 검증
```

AI 모델이 완성될 때까지 통합 작업을 기다리지 않는다. lee는 eom이 제공한 Example·Fixture로 먼저 연결하고, 실제 AI API 준비 후 Client 설정만 교체한다.

## 첫 번째 공동 완료 기준

```text
Frontend /
  ↓ POST /api/cases/analyze
General API (lee)
  ↓ 병렬 내부 호출
AI API (eom): WindowAI + Full Context LLM
  ↓ 구조화된 결과
General API: 검증·Fusion 결과 수용·Case 저장
  ↓
/cases/:caseId 이동
```
