# Database migrations

General API가 소유하는 MySQL 서비스 DB의 versioned migration을 둔다.

`MVP_v3/.env`에 MySQL 접속 정보를 입력한 뒤 이후 versioned migration을 적용한다.

```powershell
cd MVP_v3/backend
python scripts/apply_migrations.py
```

적용된 파일은 `schema_migrations`에 전체 파일명으로 기록되므로 같은 명령을 다시 실행해도 중복 적용되지 않는다.
최초 빈 `csr` DB는 `MVP_v3/database/01_mysql_csr_schema.sql`로 생성한다. 기본 스키마에는 001~013의 현재 결과와 Context Panel V3의 기본 컬럼·추출 job이 포함되어 있으며, 이미 반영한 001~013 및 `015_context_panel_v3.sql`을 적용 이력에 기록한다. 이후 migration runner가 `014_case_context_v2_foundation.sql`, `015_case_number_sequence.sql`처럼 기본 스키마에 포함되지 않은 파일만 적용한다. 그다음 `.env`의 `CASE_REPOSITORY=mysql`을 확인하고 General API를 재시작한다.

기본 스키마와 migration marker는 반드시 함께 갱신한다. 예를 들어 메시지 멱등 UNIQUE KEY가 기본 스키마에 존재하면 `011_message_idempotency.sql`도 적용 이력에 있어야 하며, 그렇지 않으면 신규 DB에서 runner가 같은 인덱스를 다시 추가하려다 실패한다.

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

`014_case_context_v2_foundation.sql` adds the approved, separated storage
foundation for facts, gaps, AI suggestions, staff tasks, decision records and
their audit history. It is additive and does not connect the existing v1 UI or
API to the new tables. The rollback SQL is isolated under `migrations/rollback/`
so the normal migration runner cannot apply it accidentally. Destructive
rollback is allowed only before v2 data is written or after a verified export;
after writes, disable the feature and use a reviewed data migration instead.
The migration deliberately avoids a cyclic foreign key between suggestions and
tasks so a partially applied MySQL DDL batch can be safely rerun before the
schema-migration marker is written. The application transaction must keep
`accepted_task_id` and `source_suggestion_id` consistent.

`015_case_number_sequence.sql` adds the monotonic `VP-N` allocator used by
case creation. `015_context_panel_v3.sql` adds structured customer answers and
durable Message→Fact extraction jobs. The two files share a numeric prefix but
are tracked by their full filenames; do not rename or treat one as replacing
the other. The Context Panel migration has a reviewed rollback under
`migrations/rollback/`, while the sequence table is required by current case
creation and has no routine destructive rollback.

For a database whose tables predate `schema_migrations`, verify its schema and
apply a reviewed subset with repeated `--only FILENAME` options. This avoids
blindly replaying old non-idempotent `ALTER TABLE` files. The option is not a
license to skip dependencies; the operator must select them in order.
