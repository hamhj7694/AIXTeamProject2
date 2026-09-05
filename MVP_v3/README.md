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
| `MYSQL_USER`, `MYSQL_DATABASE` | 실제 MySQL 계정과 DB 이름; 예제는 `ham`, `csr` |
| `MYSQL_PASSWORD` | `MYSQL_USER` 계정의 실제 비밀번호 |
| `MYSQL_ROOT_PASSWORD` | 포함된 MySQL 컨테이너를 사용할 때 설정할 별도 비밀번호 |
| `CASE_ADMIN_DELETE_PASSWORD` | 사건 종결·휴지통·복구·영구 삭제용 긴 관리자 비밀번호 |
| `MYSQL_HOST` | 로컬 MySQL은 `127.0.0.1`, RDS 직접 실행은 RDS endpoint |
| `DEPLOY_MYSQL_HOST` | Docker Compose는 내장 DB면 `mysql`, 외부 RDS면 RDS endpoint |
| `CORS_ALLOWED_ORIGINS` | Frontend와 API를 서로 다른 도메인으로 배포할 때 Frontend origin |
| `APP_PORT` | Docker Compose가 외부에 공개할 Frontend 포트 |
| `MVP_OPEN_PERMISSIONS` | 로컬 시연은 `1`: 은행 화면의 참여자 역할 제한 해제. `0`: 기존 역할 검사 유지 |

`MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD`, `CASE_ADMIN_DELETE_PASSWORD`는 서로
다른 20자 이상의 임의 문자열을 권장한다. `MYSQL_PASSWORD`를 바꾸면 실제
MySQL의 `MYSQL_USER` 계정 비밀번호도 같은 값으로 변경해야 한다.

Nginx와 함께 배포하는 기본 구성에서는 Frontend가 같은 origin의 `/api`를
사용하므로 `frontend/.env`와 `VITE_API_BASE_URL`은 필요하지 않다. AWS에서는
루트 `.env` 파일을 업로드하지 않고 같은 키를 Secrets Manager나 서비스
환경변수로 등록한다.

## 다른 PC에서 수동 최초 설치 및 실행

아래는 Windows PowerShell 기준이다. Python 3.11을 권장하며 Docker도 3.11을
사용한다. Python 3.11 이상의 다른 버전을 사용한다면 고정된
`scikit-learn==1.6.1`을 포함한 의존성 설치 성공을 먼저 확인한다.
Node.js LTS와 npm, 실행 중인 MySQL 8.x 및 MySQL 명령행 클라이언트가 필요하다.
Docker의 MySQL 기준 버전은 8.4다. 다른 PC에서의 실제 설치 검증은 아직 수행하지 않았다.

### 1. 작업 폴더와 환경설정

**이 문서의 이후 상대 경로는 모두 `MVP_v3` 폴더 기준이다.** 전체 저장소를
받았다면 저장소 최상위에서 다음을 한 번 실행한다. `MVP_v3` 폴더만 전달받아
이미 그 안에 있다면 `cd MVP_v3`를 다시 실행하지 않는다.

```powershell
cd MVP_v3
```

`.env`가 없을 때만 예제를 복사한 뒤 로컬 편집기로 값을 입력한다.
기존 PC의 `.env`, `.venv`, `frontend/node_modules`는 제출물에 포함하거나
새 PC로 복사하지 않는다.

```powershell
if (-not (Test-Path -LiteralPath .env)) { Copy-Item .env.example .env }
python --version
node --version
npm.cmd --version
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
npm.cmd --prefix frontend ci
```

진행 전에 `.env`의 `OPENAI_API_KEY`, `MYSQL_HOST`, `MYSQL_PORT`,
`MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`, `CASE_ADMIN_DELETE_PASSWORD`를
확인한다. `replace_with_...` 예제 값은 실제 값으로 교체한다.
수동 실행에서는 `MYSQL_ROOT_PASSWORD`가 필요하지 않다.
ML 모델은 `backend/ai_api/models`에 포함되어 있어 별도 다운로드가 필요 없다.

### 2. 빈 DB 초기화와 추가 migration

MySQL에 `MYSQL_DATABASE`와 `MYSQL_USER` 계정을 먼저 준비한다. 아래 예제는
`.env`와 동일한 `ham` 계정, `csr` DB를 사용한다. DB 관리자가 `csr` DB를
`utf8mb4`로 생성하고 해당 계정에 `csr.*`의 테이블 읽기·쓰기 및
schema 생성·변경·인덱스·외래키·TRIGGER 권한을 부여해야 한다.
`.env`의 비밀번호를 바꾸는 것만으로 실제 MySQL 계정 비밀번호가 바뀌지는 않는다.

`MVP_v3` 폴더에서 접속한다. 호스트·포트·계정·DB가 다르면 `.env`에 맞춰 바꾼다.
비밀번호는 프롬프트에 입력한다.

```powershell
mysql --host=127.0.0.1 --port=3306 --user=ham --password csr
```

MySQL 프롬프트에서 **최초의 빈 DB에만** 기본 스키마를 적용한다.

```sql
SOURCE database/01_mysql_csr_schema.sql;
EXIT;
```

이 파일은 `001`~`013`을 적용한 기준선을 기록한다. **기본 스키마만으로는
사건 맥락 v2가 동작하지 않는다.** PowerShell로 돌아와 API를 시작하기 전에
추가 migration을 적용한다. 이 명령은 `MVP_v3/.env`를 읽고 적용 이력이 없는
파일을 순서대로 실행하며, 현재 새 DB에는 `014_case_context_v2_foundation.sql`을 적용한다.

```powershell
./.venv/Scripts/python.exe backend/scripts/apply_migrations.py
```

이미 서비스 중인 DB에는 기본 스키마를 다시 넣지 않는다. DB를 백업하고
General API를 중지한 뒤 migration을 적용한다. `schema_migrations`에
정상 이력이 있으면 같은 명령은 이미 적용한 파일을 건너뛴다. 이력이 없는
오래된 DB는 실제 스키마와 선행 migration을 확인한 후에만 `--only`로
대상 파일을 지정한다. `013`까지 적용된 것이 확인된 DB의 `014` 추가 명령은 다음과 같다.

```powershell
./.venv/Scripts/python.exe backend/scripts/apply_migrations.py --only 014_case_context_v2_foundation.sql
```

### 3. 서버 실행

각각의 새 터미널을 `MVP_v3` 폴더에서 열고 아래 세 명령 묶음을 하나씩 실행한다.
설치와 migration 단계가 모두 성공한 뒤 시작한다.

AI API:

```powershell
cd backend
../.venv/Scripts/python.exe -m uvicorn ai_api.app.main:app --host 127.0.0.1 --port 8101
```

General API:

```powershell
cd backend
../.venv/Scripts/python.exe -m uvicorn general_api.app.main:app --host 127.0.0.1 --port 8100
```

Frontend:

```powershell
cd frontend
npm.cmd run dev
```

접속: `http://127.0.0.1:5176`. API 연결은 `http://127.0.0.1:8100/health`와
`http://127.0.0.1:8101/health`로 확인한다. 건강 상태 응답만으로 실제 AI 응답이나
전체 브라우저 흐름까지 검증된 것은 아니므로 새 통화 분석과 채팅도 직접 확인한다.

### 로컬 시연의 역할 설정

`MVP_v3/.env`에 `MVP_OPEN_PERMISSIONS=1`을 설정하면 은행 화면에서는
참여자 등록이나 검토자 지정 없이 역할로 제한되던 업무를 사용할 수 있다.
고객 화면에 은행 내부 기록을 공개하는 설정은 아니며, 고객 공개 범위와
종결·휴지통·복구·영구 삭제의 관리자 비밀번호 검사는 유지한다.
`MVP_OPEN_PERMISSIONS=0`으로 설정하면 기존 참여자 역할 검사를 사용한다.
예제 `.env`는 `1`이며 변수를 설정하지 않으면 서버는 `0`으로 동작한다.
수동 실행에서는 값을 바꾼 뒤 General API를 재시작한다. Docker Compose에서는
`docker compose up -d --force-recreate general-api`로 변경된 환경변수를 반영한다.

권한 개방은 신뢰할 수 있는 사용자의 로컬 시연 전용이며 운영 환경에서 사용하지 않는다.
`0`도 실제 로그인 세션이나 운영형 인증/RBAC를 추가하는 설정은 아니다.

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

Docker Compose가 설치되어 있다면 `MVP_v3` 폴더에서 다음 순서로 실행한다.
현재 인증 구조는 로컬 시연용이며, 인터넷 공개 운영 전에는 별도의 인증 설계가 필요하다.

```powershell
if (-not (Test-Path -LiteralPath .env)) { Copy-Item .env.example .env }
# .env의 OPENAI/MySQL/관리자 비밀번호를 실제 Secret 값으로 교체
docker compose up --build -d
```

외부 Amazon RDS를 Docker Compose에서 사용할 때는 `.env`의
`DEPLOY_MYSQL_HOST`를 RDS endpoint로 설정한다. FastAPI와 migration 스크립트를
컨테이너 없이 직접 실행할 때는 `MYSQL_HOST`와 `MYSQL_PORT`를 사용하므로
이 값도 RDS 접속 정보로 맞춘다. RDS에 접속 가능한 PC에서 위의
**빈 DB 초기화 → 추가 migration** 절차를 모두 수행한 뒤 서비스를 시작한다.
기본 SQL만 RDS에 적용하면 `014`의 v2 테이블이 누락된다.

내장 MySQL의 **새 volume**에는 Compose가 기본 스키마와 `014`를 순서대로
자동 적용한다. **기존 volume**에서는 초기화 SQL이 다시 실행되지 않는다.
`013`까지만 있는 기존 DB는 백업 및 General API 중지 후 `014`를 별도로
적용하고 재시작해야 한다. 이 Compose는 MySQL 포트를 호스트에 공개하지 않으므로
기존 내장 DB 작업은 컨테이너 내부의 MySQL 클라이언트를 이용한다.
외부 DB는 접속 가능한 환경에서 위 migration 명령을 사용한다.
데이터가 있는 volume을 지워서 migration을 대신하지 않는다.

운영 Secret은 `.env`를 이미지에 복사하지 말고 AWS Secrets Manager나 배포
환경변수로 주입한다. 기본 컨테이너 구성은 MySQL volume과 첨부파일 volume을
사용하며 외부에는 Frontend 포트만 공개한다.

## 검증

새 터미널의 `MVP_v3` 폴더에서 실행한다.

```powershell
cd frontend
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
