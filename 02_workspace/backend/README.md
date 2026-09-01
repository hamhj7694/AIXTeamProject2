# Backend workspace

백엔드 코드는 작업자 이름이 아니라 실행 책임과 도메인을 기준으로 나눈다.

```text
backend/
├─ general_api/          # Frontend가 호출하는 공개 Backend API
├─ ai_api/               # general_api가 내부 호출하는 AI API
├─ contracts/            # 서비스 사이의 요청·응답 계약
├─ migrations/           # 공용 DB migration
├─ docker/               # 로컬·배포 실행 환경
└─ experiments/          # 담당자별 폐기 가능한 실험 코드
```

## 의존 방향

```text
Frontend -> general_api -> ai_api
                  |
                  +-> Database / Realtime

general_api + ai_api -> contracts
```

- Frontend는 `ai_api`를 직접 호출하지 않는다.
- `ai_api`는 서비스 DB를 직접 수정하지 않고 구조화된 결과만 반환한다.
- 운영 코드에서 `experiments`를 import하지 않는다.
- 공통 진입점, 설정, 계약 파일은 동시에 여러 명이 수정하지 않는다.

## 현재 담당 경계

| 담당자 | 주 작업 영역 |
|---|---|
| eom | `general_api/app/domains/diagnosis`, `cases` 초기 생성, `ai_api/app/domains/diagnosis` |
| lee | `ai_api/app/domains/report`, `case_support`, `knowledge` |
| ham | 추후 `general_api/app/domains/realtime`, `voice`, `verification`, `actions` |

세부 작업 배정은 `01_docs/03_Backend_document_md/team_work/` 문서를 따른다.

