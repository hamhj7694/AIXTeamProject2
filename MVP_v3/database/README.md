# MySQL 초기화

`01_mysql_csr_schema.sql`은 MVP_v3 FastAPI가 사용할 빈 MySQL 스키마다. 기존 SQLite 데이터와 Case 데이터는 포함하지 않는다.

이미 `csr` 데이터베이스가 있다면 저장소 최상위 폴더에서 접속한다.

```powershell
mysql -u ham -p csr
```

비밀번호를 입력한 뒤 MySQL prompt에서 초기화 파일을 실행한다.

```sql
SOURCE MVP_v3/database/01_mysql_csr_schema.sql;
SHOW TABLES;
SELECT COUNT(*) AS case_count FROM cases;
```

`csr`이 아직 없다면 MySQL 접속 후 아래를 먼저 실행한다.

```sql
CREATE DATABASE csr CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

FastAPI의 환경변수는 아래처럼 설정한다. 비밀번호와 OpenAI 키는 Git에 저장하지 않고 AWS Secrets Manager 또는 배포 환경변수로 주입한다.

```text
CASE_REPOSITORY=mysql
MYSQL_HOST=<RDS endpoint 또는 DB host>
MYSQL_PORT=3306
DEPLOY_MYSQL_HOST=<Docker Compose에서 사용할 RDS endpoint, 내장 DB면 mysql>
DEPLOY_MYSQL_PORT=3306
MYSQL_USER=ham
MYSQL_PASSWORD=<secret>
MYSQL_DATABASE=csr
AI_API_BASE_URL=http://<ai-api-host>:8101
```

`MVP_v3/.env.example`을 `MVP_v3/.env`로 복사한 뒤 실제 Secret 값을 로컬에서 입력할 수 있다. `.env`는 Git에 커밋하지 않는다.

General API는 시작할 때 MySQL에 `SELECT 1`을 실행한다. 연결 또는 인증에 실패하면 서버 시작도 실패하므로 잘못된 설정을 바로 확인할 수 있다. 실행 후 `/health`는 다음 형태로 DB 연결 상태를 반환한다.

```json
{"status":"ok","database":"mysql"}
```
