# Backend workspace

백엔드 코드는 작업자 이름이 아니라 실행 책임과 도메인을 기준으로 나눈다.

```text
backend/
├─ general_api/          # Frontend가 호출하는 공개 Backend API
├─ ai_api/               # general_api가 내부 호출하는 AI API
├─ contracts/            # 서비스 사이의 요청·응답 계약
├─ migrations/           # 공용 DB migration
├─ docker/               # 로컬·배포 실행 환경
└─ experiments/          # 운영 코드와 분리된 폐기 가능한 실험 코드
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
| A=eom | `general_api/**`, `contracts/public_api/**`, `migrations/**`, Case Platform |
| B=lee | `ai_api/**`, `contracts/ai_internal/**`, AI 모델·Agent·RAG·평가 |
| C=ham | `frontend/**`, Realtime·통합 E2E·`docker/**` |

- 공개 API Contract는 A가 최종 편집하고 C가 소비자 관점에서 Review한다.
- AI 내부 Contract는 B가 최종 편집하고 A가 소비자 관점에서 Review한다.
- 과거 구현 기여는 유지하며 향후 소유권만 위 기준으로 전환한다.

세부 작업 배정은 `01_docs/03_Backend_document_md/team_work/` 문서를 따른다.

## 최초 진단 Vertical Slice 실행

```powershell
cd 02_workspace/backend
python -m pip install -r requirements.txt
python -m unittest discover -s ai_api/tests -v
python -m unittest discover -s general_api/tests -v
```

로컬에서 OpenAI 호출 없이 흐름만 확인할 때는 두 서버를 시작하기 전에
`DIAGNOSIS_EXTRACTOR_MODE=fixture`를 설정한다. 실제 분석에서는 `openai`와
`OPENAI_API_KEY`를 사용한다. 비밀키는 저장소에 커밋하지 않는다.
