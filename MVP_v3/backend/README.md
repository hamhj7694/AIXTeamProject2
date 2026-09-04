# Backend workspace

백엔드 코드는 작업자 이름이 아니라 실행 책임과 도메인을 기준으로 나눈다.

```text
backend/
├─ general_api/          # Frontend가 호출하는 공개 Backend API
├─ ai_api/               # general_api가 내부 호출하는 AI API
├─ contracts/            # 서비스 사이의 요청·응답 계약
├─ migrations/           # 이후 변경용 versioned MySQL migration
└─ scripts/              # Migration·OpenAPI 보조 명령
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

## MySQL `csr` 연결

빈 스키마는 `MVP_v3/database/01_mysql_csr_schema.sql`에 있다.

```powershell
mysql -u ham -p csr
```

MySQL prompt에서 실행한다.

```sql
SOURCE MVP_v3/database/01_mysql_csr_schema.sql;
```

그다음 Backend 환경 파일을 만든다.

```powershell
cd MVP_v3/backend
Copy-Item ../.env.example ../.env
```

`MVP_v3/.env`에서 `OPENAI_API_KEY`, `MYSQL_PASSWORD`, `CASE_ADMIN_DELETE_PASSWORD`를 실제 값으로 바꾼다. `.env`와 AWS Secret은 Git에 커밋하지 않는다.

## 최초 진단 Vertical Slice 실행

```powershell
cd MVP_v3/backend
python -m pip install -r requirements.txt
python -m unittest discover -s ai_api/tests -v
python -m unittest discover -s general_api/tests -v
```

로컬 서버는 서로 다른 터미널에서 실행한다.

```powershell
# AI API
python -m uvicorn ai_api.app.main:app --host 127.0.0.1 --port 8101

# General API
python -m uvicorn general_api.app.main:app --host 127.0.0.1 --port 8100
```

General API는 시작 시 MySQL에 `SELECT 1`을 실행한다. 연결이 실패하면 서버가 준비 완료 상태로 뜨지 않는다. 실행 후 `http://127.0.0.1:8100/health`에서 `{"status":"ok","database":"mysql"}`을 확인한다.

실제 분석에는 `OPENAI_API_KEY`가 필요하다. 목데이터 실행 모드는 제공하지 않으며,
비밀키는 저장소에 커밋하지 않는다.
