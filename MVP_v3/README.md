# CONTEXT-FIRST CASE Frontend V3

V3는 은행 담당자가 하나의 Shared Case에서 사건 맥락, 고객 대화, 기관 확인과 대응 업무를 처리하는 별도 서비스다. Frontend와 FastAPI Backend를 모두 `MVP_v3` 아래에서 실행한다.

## 실행 구조

```text
Browser :5176
  └─ /api proxy → General API :8100
                       ├─ MySQL Repository
                       └─ AI API :8101
```

Frontend가 AI API를 직접 호출하지 않는다. General API가 필요한 Case Context만 AI API에 전달한다.

## 환경변수 위치

환경변수 파일은 루트의 `MVP_v3/.env` 하나만 사용한다. AI API, General API,
migration 스크립트와 Docker Compose가 모두 이 파일을 기준으로 동작한다.
`backend/.env`나 `frontend/.env`는 만들지 않는다.

| 키 | 사용자가 수정할 내용 |
|---|---|
| `OPENAI_API_KEY` | 실제 OpenAI API 키 |
| `MYSQL_PASSWORD` | `MYSQL_USER` 계정의 실제 비밀번호 |
| `MYSQL_ROOT_PASSWORD` | 포함된 MySQL 컨테이너를 사용할 때 설정할 별도 비밀번호 |
| `CASE_ADMIN_DELETE_PASSWORD` | 사건 종결·휴지통·복구·영구 삭제용 긴 관리자 비밀번호 |
| `MYSQL_HOST` | 로컬 MySQL은 `127.0.0.1`, RDS 직접 실행은 RDS endpoint |
| `DEPLOY_MYSQL_HOST` | Docker Compose는 내장 DB면 `mysql`, 외부 RDS면 RDS endpoint |
| `CORS_ALLOWED_ORIGINS` | Frontend와 API를 서로 다른 도메인으로 배포할 때 Frontend origin |
| `APP_PORT` | Docker Compose가 외부에 공개할 Frontend 포트 |

`MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD`, `CASE_ADMIN_DELETE_PASSWORD`는 서로
다른 20자 이상의 임의 문자열을 권장한다. `MYSQL_PASSWORD`를 바꾸면 실제
MySQL의 `MYSQL_USER` 계정 비밀번호도 같은 값으로 변경해야 한다.

Nginx와 함께 배포하는 기본 구성에서는 Frontend가 같은 origin의 `/api`를
사용하므로 `frontend/.env`와 `VITE_API_BASE_URL`은 필요하지 않다. AWS에서는
루트 `.env` 파일을 업로드하지 않고 같은 키를 Secrets Manager나 서비스
환경변수로 등록한다.

## 실행

Backend와 AI API는 `MVP_v3/backend`에서 실행한다. 먼저 루트의 `.env.example`을 `.env`로 복사하고, `database/01_mysql_csr_schema.sql`을 `csr` 데이터베이스에 적용한다. 로컬 실행과 Docker Compose 모두 같은 `MVP_v3/.env`를 사용한다.

ML 학습 환경과 맞추기 위해 프로젝트 전용 가상환경(scikit-learn 1.6.1)을 사용한다. 최초 설치:

```powershell
python -m venv MVP_v3/.venv
MVP_v3/.venv/Scripts/python.exe -m pip install -r MVP_v3/backend/requirements.txt
```

각 터미널에서 API 하나씩 실행한다:

```powershell
cd MVP_v3/backend
../.venv/Scripts/python.exe -m uvicorn ai_api.app.main:app --host 127.0.0.1 --port 8101
```

```powershell
cd MVP_v3/backend
../.venv/Scripts/python.exe -m uvicorn general_api.app.main:app --host 127.0.0.1 --port 8100
```

V3 Frontend:

```powershell
cd MVP_v3/frontend
npm.cmd install
npm.cmd run dev
```

접속: `http://127.0.0.1:5176`

## MVP_v3 단독 배포

`MVP_v3`에는 Frontend, General API, AI API, 공용 Contract, Window AI 모델,
MySQL 초기 스키마와 컨테이너 실행 설정이 모두 들어 있다. 상위 폴더나
`MVP_v2`, `02_workspace` 파일을 참조하지 않는다.

```text
MVP_v3/
├─ frontend/          # React 빌드 + Nginx 및 /api reverse proxy
├─ backend/
│  ├─ general_api/    # Frontend 공개 FastAPI
│  ├─ ai_api/         # ML·LLM FastAPI와 Window AI 모델
│  ├─ contracts/      # 두 API가 공유하는 Pydantic Contract
│  ├─ migrations/     # 기존 DB 증분 migration
│  └─ scripts/        # migration/OpenAPI 유틸리티
├─ database/          # 신규 MySQL용 빈 서비스 스키마
├─ docker-compose.yml # 전체 서비스 묶음 실행
└─ .env.example       # 배포 환경변수 이름과 예시
```

Docker 기반 AWS 배포 또는 EC2 검증은 다음 순서로 실행한다.

```powershell
cd MVP_v3
Copy-Item .env.example .env
# .env의 OPENAI/MySQL/관리자 비밀번호를 실제 Secret 값으로 교체
docker compose up --build -d
```

외부 Amazon RDS를 Docker Compose에서 사용할 때는 `.env`의
`DEPLOY_MYSQL_HOST`를 RDS endpoint로 설정한다. FastAPI를 컨테이너 없이 직접
실행할 때는 `MYSQL_HOST`를 사용한다. 그리고
`database/01_mysql_csr_schema.sql`을 RDS의 `csr` DB에 한 번 적용한다.
운영 Secret은 `.env`를 이미지에 복사하지 말고 AWS Secrets Manager나 배포
환경변수로 주입한다. 기본 컨테이너 구성은 MySQL volume과 첨부파일 volume을
사용하며 외부에는 Frontend 포트만 공개한다.

## 검증

```powershell
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
```

## 핵심 문서

- 제품 요구사항: `PRD.md`
- 고객용 제품 요구사항: `CUSTOMER_PRD.md`
- **작업 시작 시 반드시 먼저 읽는 단일 기준 문서**: `docs/03_IMPLEMENTATION_STATUS.md`
- 개발 매핑: `docs/01_WORK_MAPPING.md`
- 세부 이력·장기 백로그: `docs/02_DETAILED_TODO.md`
- 사건 맥락 v2 승인 데이터 계약과 단계별 구현 경계: `docs/09_CASE_CONTEXT_DATA_CONTRACT.md`
- 사건 종결 AI 보고서 형식·저장·공개 계약: `docs/10_FINAL_CASE_REPORT_CONTRACT.md`

## 안전 경계

- 고객 공개 메시지와 은행 내부 기록의 대상을 입력 전에 명확히 선택한다.
- AI 결과는 분석·권고이며 금융기관의 최종 결정으로 표시하지 않는다.
- Action 등록은 실제 지급정지나 신고 실행이 아니라 담당 업무 기록이다.
- 5초 polling은 Case/Bundle/Fact만 갱신한다. AI Brief endpoint는 반복 polling하지 않는다.
- 실제 인증/RBAC와 SSE/WebSocket은 현재 Backend 후속 과제다.
