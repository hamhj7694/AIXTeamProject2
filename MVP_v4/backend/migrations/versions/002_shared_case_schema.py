"""002: V4 Shared Case schema; all entities are V4-owned and versioned."""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

UUID = sa.String(36)
VISIBILITY = ("CUSTOMER", "BANK_INTERNAL", "AI_PRIVATE")


def _audit_columns(*, case_id: bool = True, visibility: bool = True) -> list[sa.Column]:
    columns = []
    if case_id:
        columns.append(sa.Column("case_id", UUID, sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True))
    if visibility:
        columns.append(sa.Column("visibility", sa.String(20), nullable=False, server_default="BANK_INTERNAL"))
    columns.extend([
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(128), nullable=True),
        sa.Column("updated_by", sa.String(128), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ])
    return columns


def _visibility_check(name: str) -> sa.CheckConstraint:
    values = ", ".join(f"'{value}'" for value in VISIBILITY)
    return sa.CheckConstraint(f"visibility IN ({values})", name=name)


def _create_case_scoped(name: str, extra: list[sa.Column], *, visibility: bool = True,
                        constraints: list[sa.Constraint] | None = None) -> None:
    arguments: list[sa.Column | sa.Constraint] = [sa.Column("id", UUID, primary_key=True)]
    arguments.extend(_audit_columns(visibility=visibility))
    arguments.extend(extra)
    if visibility:
        arguments.append(_visibility_check(f"ck_{name}_visibility"))
    arguments.extend(constraints or [])
    op.create_table(name, *arguments)


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("case_number", sa.String(40), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="TRIAGE"),
        sa.Column("mode", sa.String(20), nullable=False, server_default="PREVENT"),
        sa.Column("loss_status", sa.String(20), nullable=False, server_default="UNKNOWN"),
        sa.Column("primary_assignee_id", sa.String(128), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(128), nullable=True),
        sa.Column("updated_by", sa.String(128), nullable=True),
        sa.CheckConstraint("status IN ('TRIAGE', 'ACTIVE', 'CLOSED')", name="ck_cases_status"),
        sa.CheckConstraint("mode IN ('PREVENT', 'RECOVERY')", name="ck_cases_mode"),
        sa.CheckConstraint("loss_status IN ('UNKNOWN', 'NO_LOSS', 'LOSS_CONFIRMED')", name="ck_cases_loss_status"),
        sa.CheckConstraint("revision >= 1", name="ck_cases_revision"),
        sa.CheckConstraint("version >= 1", name="ck_cases_version"),
        sa.CheckConstraint("length(fingerprint) = 64", name="ck_cases_fingerprint_length"),
    )
    op.create_index("ix_cases_status_updated", "cases", ["status", "updated_at"])

    _create_case_scoped("case_participants", [
        sa.Column("participant_id", sa.String(128), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.UniqueConstraint("case_id", "participant_id", "role", name="uq_case_participants_case_member_role"),
        sa.CheckConstraint("role IN ('CUSTOMER', 'BANK_STAFF')", name="ck_case_participants_role"),
    ], visibility=False)

    _create_case_scoped("context_features", [
        sa.Column("source_event_id", sa.String(128), nullable=False),
        sa.Column("schema_version", sa.String(40), nullable=False),
        sa.Column("feature_fingerprint", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("case_id", "source_event_id", name="uq_context_features_case_source_event"),
        sa.CheckConstraint("length(feature_fingerprint) = 64", name="ck_context_features_fingerprint_length"),
    ], visibility=False)
    _create_case_scoped("context_items", [
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("source_entity_id", UUID, nullable=True),
        sa.Column("confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
    ])
    _create_case_scoped("messages", [
        sa.Column("sender_role", sa.String(20), nullable=False),
        sa.Column("sender_id", sa.String(128), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("client_request_id", UUID, nullable=True),
        sa.UniqueConstraint("case_id", "client_request_id", name="uq_messages_case_client_request"),
        sa.CheckConstraint("sender_role IN ('CUSTOMER', 'BANK_STAFF', 'SYSTEM', 'AI')", name="ck_messages_sender_role"),
    ])
    _create_case_scoped("questions", [
        sa.Column("priority", sa.String(4), nullable=False),
        sa.Column("target_field", sa.String(80), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("requires_human_approval", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("priority IN ('P0', 'P1', 'P2')", name="ck_questions_priority"),
    ])
    _create_case_scoped("question_answers", [
        sa.Column("question_id", UUID, sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("answer_value", sa.JSON(), nullable=False),
        sa.Column("answered_by", sa.String(128), nullable=True),
    ])
    _create_case_scoped("facts", [
        sa.Column("field_key", sa.String(120), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="CANDIDATE"),
        sa.Column("source_entity_id", UUID, nullable=True),
        sa.CheckConstraint("status IN ('CANDIDATE', 'CONFIRMED', 'REJECTED')", name="ck_facts_status"),
    ])
    _create_case_scoped("verifications", [
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("customer_visible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint("status IN ('PENDING', 'IN_PROGRESS', 'VERIFIED', 'MISMATCH', 'UNVERIFIABLE')", name="ck_verifications_status"),
    ])
    _create_case_scoped("verification_evidence", [
        sa.Column("verification_id", UUID, sa.ForeignKey("verifications.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("source_id", sa.String(160), nullable=False),
        sa.Column("title", sa.String(400), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("content", sa.Text(), nullable=False),
    ])
    _create_case_scoped("tasks", [
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="TODO"),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("client_request_id", UUID, nullable=True),
        sa.UniqueConstraint("case_id", "client_request_id", name="uq_tasks_case_client_request"),
        sa.CheckConstraint("status IN ('TODO', 'IN_PROGRESS', 'BLOCKED', 'COMPLETED', 'CANCELLED')", name="ck_tasks_status"),
    ], visibility=False)
    _create_case_scoped("customer_progress", [
        sa.Column("step", sa.String(80), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.UniqueConstraint("case_id", "step", name="uq_customer_progress_case_step"),
    ])
    _create_case_scoped("ai_suggestions", [
        sa.Column("suggestion_type", sa.String(60), nullable=False),
        sa.Column("proposal", sa.JSON(), nullable=False),
        sa.Column("source_revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.CheckConstraint("status IN ('PENDING', 'ACCEPTED', 'EDITED', 'REJECTED', 'STALE')", name="ck_ai_suggestions_status"),
        sa.CheckConstraint("source_revision >= 1", name="ck_ai_suggestions_revision"),
    ])
    _create_case_scoped("case_events", [
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", UUID, nullable=True),
        sa.Column("actor_role", sa.String(20), nullable=False),
        sa.Column("actor_id", sa.String(128), nullable=True),
        sa.Column("case_revision", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.CheckConstraint("event_type IN ('CASE_CREATED', 'CASE_UPDATED', 'ENTITY_CREATED', 'ENTITY_UPDATED', 'ENTITY_DELETED')", name="ck_case_events_type"),
        sa.CheckConstraint("actor_role IN ('CUSTOMER', 'BANK_STAFF', 'SYSTEM', 'AI')", name="ck_case_events_actor_role"),
        sa.CheckConstraint("case_revision >= 1", name="ck_case_events_revision"),
    ])
    op.create_index("ix_case_events_case_revision", "case_events", ["case_id", "case_revision"])
    _create_case_scoped("case_briefs", [
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_revision", sa.Integer(), nullable=False),
        sa.Column("trigger", sa.String(60), nullable=False),
        sa.CheckConstraint("source_revision >= 1", name="ck_case_briefs_revision"),
    ], visibility=False)
    _create_case_scoped("reports", [
        sa.Column("report_type", sa.String(30), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("source_revision", sa.Integer(), nullable=False),
        sa.UniqueConstraint("case_id", "report_type", name="uq_reports_case_type"),
        sa.CheckConstraint("report_type IN ('FINAL')", name="ck_reports_type"),
    ], visibility=False)
    _create_case_scoped("ai_runs", [
        sa.Column("route", sa.String(20), nullable=False),
        sa.Column("intent", sa.String(80), nullable=True),
        sa.Column("agent_name", sa.String(80), nullable=True),
        sa.Column("tool_names", sa.JSON(), nullable=False),
        sa.Column("model", sa.String(120), nullable=True),
        sa.Column("prompt_version", sa.String(80), nullable=True),
        sa.Column("source_revision", sa.Integer(), nullable=False),
        sa.Column("case_fingerprint", sa.String(64), nullable=False),
        sa.Column("schema_valid", sa.Boolean(), nullable=False),
        sa.Column("grounding_sources", sa.JSON(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(12, 6), nullable=True),
        sa.Column("human_action", sa.String(20), nullable=False, server_default="NONE"),
        sa.Column("error_type", sa.String(80), nullable=True),
        sa.CheckConstraint("route IN ('DIRECT', 'RAG', 'TOOL', 'AGENT', 'COMPOSITE')", name="ck_ai_runs_route"),
    ], visibility=False)
    _create_case_scoped("personal_notes", [
        sa.Column("owner_id", sa.String(128), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
    ], visibility=False)
    _create_case_scoped("bookmarks", [
        sa.Column("owner_id", sa.String(128), nullable=False),
        sa.Column("target_entity_type", sa.String(40), nullable=False),
        sa.Column("target_entity_id", UUID, nullable=False),
        sa.UniqueConstraint("case_id", "owner_id", "target_entity_type", "target_entity_id", name="uq_bookmarks_owner_target"),
    ], visibility=False)
    _create_case_scoped("attachments", [
        sa.Column("storage_key", sa.String(500), nullable=False, unique=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.CheckConstraint("byte_size >= 0", name="ck_attachments_byte_size"),
        sa.CheckConstraint("length(sha256) = 64", name="ck_attachments_sha256_length"),
    ])
    op.create_table(
        "official_contacts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization", sa.String(300), nullable=False),
        sa.Column("contact_type", sa.String(30), nullable=False),
        sa.Column("value", sa.String(500), nullable=False),
        sa.Column("source_id", sa.String(160), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("contact_type IN ('PHONE', 'URL', 'ADDRESS')", name="ck_official_contacts_type"),
        sa.CheckConstraint("version >= 1", name="ck_official_contacts_version"),
    )
    op.create_table(
        "idempotency_keys",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("case_id", UUID, sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("client_request_id", UUID, nullable=False),
        sa.Column("operation", sa.String(80), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("response_entity_type", sa.String(40), nullable=True),
        sa.Column("response_entity_id", UUID, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("case_id", "client_request_id", "operation", name="uq_idempotency_case_request_operation"),
        sa.CheckConstraint("length(request_fingerprint) = 64", name="ck_idempotency_fingerprint_length"),
    )


def downgrade() -> None:
    for table in [
        "idempotency_keys", "official_contacts", "attachments", "bookmarks", "personal_notes", "ai_runs", "reports",
        "case_briefs", "case_events", "ai_suggestions", "customer_progress", "tasks", "verification_evidence",
        "verifications", "facts", "question_answers", "questions", "messages", "context_items", "context_features",
        "case_participants", "cases",
    ]:
        op.drop_table(table)
