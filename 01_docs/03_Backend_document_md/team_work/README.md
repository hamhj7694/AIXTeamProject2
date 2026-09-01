# 3인 작업 운영 안내

## 현재 역할

| 작업자 | 현재 역할 | 참여 상태 |
|---|---|---|
| eom | `/` 최초 진단 Vertical Slice, WindowAI, Diagnosis LLM | ACTIVE |
| lee | Case Report·Customer/Bank AI·Knowledge RAG | ACTIVE |
| ham | 추후 독립 Backend·Realtime·Voice 영역 | WAITING |

## 폴더 구조

```text
team_work/
├─ README.md
├─ 00_task_catalog.md
├─ eom/
│  ├─ task_mapping.md
│  └─ todo.md
├─ lee/
│  ├─ task_mapping.md
│  └─ todo.md
└─ ham/
   ├─ task_mapping.md
   └─ todo.md
```

## 충돌 방지 규칙

1. 전체 배정은 조정자만 `00_task_catalog.md`에서 수정한다.
2. 각 작업자는 자신의 폴더만 진행상황 기록용으로 수정한다.
3. 다른 작업자의 소유 코드가 필요하면 직접 수정하지 않고 Contract 또는 PR Review로 요청한다.
4. 공통 설정·Entrypoint·Docker 파일은 변경 전 담당자를 지정한다.
5. 한 PR에는 원칙적으로 Task ID 하나만 포함한다.
6. Contract PR을 먼저 병합한 후 구현 PR을 병렬로 진행한다.

## 첫 번째 공동 목표

```text
Frontend /
  ↓
POST /api/cases/analyze
  ├─ WindowAI
  └─ Full Context Diagnosis LLM
       ↓
Diagnosis Fusion
  ↓
Case 저장
  ↓
/cases/:caseId 이동
```

첫 E2E가 완료되기 전에는 Voice, Realtime, 전체 RAG를 동시에 시작하지 않는다.
