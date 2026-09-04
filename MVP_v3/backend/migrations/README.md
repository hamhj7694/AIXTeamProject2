# Database migrations

General API가 소유하는 MySQL 서비스 DB의 versioned migration을 둔다.

`MVP_v3/.env`에 MySQL 접속 정보를 입력한 뒤 이후 versioned migration을 적용한다.

```powershell
cd MVP_v3/backend
python scripts/apply_migrations.py
```

적용된 파일은 `schema_migrations`에 기록되므로 같은 명령을 다시 실행해도 중복 적용되지 않는다.
최초 빈 `csr` DB는 `MVP_v3/database/01_mysql_csr_schema.sql`로 한 번에 생성할 수 있으며, 이 파일은 001~010을 적용한 것으로 기준선을 기록한다. 그다음 `.env`의 `CASE_REPOSITORY=mysql`을 확인하고 General API를 재시작한다.

