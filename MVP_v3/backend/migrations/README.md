# Database migrations

General API가 소유하는 MySQL 서비스 DB의 versioned migration을 둔다.

`MVP_v3/.env`에 MySQL 접속 정보를 입력한 뒤 이후 versioned migration을 적용한다.

```powershell
cd MVP_v3/backend
python scripts/apply_migrations.py
```

적용된 파일은 `schema_migrations`에 기록되므로 같은 명령을 다시 실행해도 중복 적용되지 않는다.
최초 빈 `csr` DB는 `MVP_v3/database/01_mysql_csr_schema.sql`로 한 번에 생성할 수 있으며, 이 파일은 001~010을 적용한 것으로 기준선을 기록한다. 그다음 `.env`의 `CASE_REPOSITORY=mysql`을 확인하고 General API를 재시작한다.

# Context item foundation (012)

`012_context_items.sql` adds protected display overlays and transactional audit
history. It does not backfill or rewrite existing Cases. The repository is not
connected to HTTP or automatic AI projection yet. Before enabling it, implement
server-authenticated Case authorization, source revision/lease checks, and update
the Case deletion/export workflow to account for these foreign-key-linked rows.
Do not delete audit history implicitly to bypass a foreign-key failure.

`013_context_projection_revision.sql` adds a monotonic semantic revision and a
single-flight/last-success projection row. Database triggers advance the revision
in the same transaction as Case fields, messages, questions/answers, facts,
verification results and actions. Presence, private notes, bookmarks and context
wording overlays are excluded. Apply this migration before enabling projection
caching in an application process.

For a database whose tables predate `schema_migrations`, verify its schema and
apply a reviewed subset with repeated `--only FILENAME` options. This avoids
blindly replaying old non-idempotent `ALTER TABLE` files. The option is not a
license to skip dependencies; the operator must select them in order.
