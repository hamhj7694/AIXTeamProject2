# Backend · AI 개발 문서 안내

> 이 파일은 `03_Backend_document_md`의 최상위 문서다.

## 폴더 구조

```text
03_Backend_document_md/
├─ 00_README.md
├─ 01_general_backend_architecture.md
├─ 02_ai_api_architecture.md
├─ 03_data_db_architecture.md
├─ 04_full_development_integration.md
├─ 05_task_mapping.md
├─ 06_progress_todo.md
├─ 07_frontend_backend_connection_schema.md
├─ ai_system_design/
│  ├─ 00_ai_system_architecture.md
│  ├─ 01_backend_workflow_orchestrator.md
│  ├─ 02_case_intelligence_ai.md
│  ├─ 03_knowledge_verification_ai.md
│  ├─ 04_case_report_ai.md
│  └─ 05_voice_intelligence_pipeline.md
└─ team_work/
   ├─ README.md
   ├─ 00_task_catalog.md
   ├─ ham/{task_mapping.md,todo.md}
   ├─ eom/{task_mapping.md,todo.md}
   └─ lee/{task_mapping.md,todo.md}
```

## 문서 역할

| 영역 | 역할 |
|---|---|
| `01~07` | Backend·AI API·DB·Frontend 연결의 공통 기준 |
| `ai_system_design` | AI와 일반 코드의 경계, 입력·출력, 호출·병렬 실행 설계 |
| `team_work/00_task_catalog.md` | 전체 Task ID, 의존성, 최초 담당자 배정 |
| `team_work/{worker}/task_mapping.md` | 개인 담당 범위, Task ID, 코드 소유권 |
| `team_work/{worker}/todo.md` | 개인 TODO, 진행상태, Blocker, 작업 로그 |

## 수정 규칙

- AI는 `01_*.md` ~ `07_*.md`를 가능한 한 수정하지 않는다.
- 공통 기준 변경을 사용자가 명시적으로 요청한 경우에만 영향과 이유를 설명하고 최소 수정한다.
- AI 시스템 책임이나 Contract 변경은 `ai_system_design`에 기록한다.
- 전체 Task 배정은 한 명의 조정자가 `team_work/00_task_catalog.md`에서 관리한다.
- ham, eom, lee는 각각 자신의 작업자 폴더만 진행상황 기록용으로 수정한다.
- 진행상황 때문에 다른 작업자의 파일이나 공통 기준 문서를 수정하지 않는다.

## 작업 순서

```text
01~07 공통 기준 확인
  ↓
ai_system_design에서 AI/일반 코드 경계 확인
  ↓
00_task_catalog에서 담당 Task 확인
  ↓
자신의 작업자 문서에 TODO·진행·로그 기록
  ↓
구현·테스트·PR
```

## 상태 값

```text
TODO / IN_PROGRESS / REVIEW / DONE / BLOCKED
```

`DONE`은 구현, Schema, 오류 처리, 테스트, 연동 확인, 작업 로그가 모두 완료된 상태다.
