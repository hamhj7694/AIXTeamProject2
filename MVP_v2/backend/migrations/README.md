# Database migrations

General API가 소유하는 MySQL 서비스 DB의 versioned migration을 둔다.

`backend/.env`에 MySQL 접속 정보를 입력한 뒤 다음 명령으로 DB와 테이블을 만든다.

```powershell
cd MVP_v2/backend
python scripts/apply_migrations.py
```

적용된 파일은 `schema_migrations`에 기록되므로 같은 명령을 다시 실행해도 중복 적용되지 않는다.
그다음 `.env`의 `CASE_REPOSITORY=mysql`로 변경하고 General API를 재시작한다.

