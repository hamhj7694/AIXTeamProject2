from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from backend.config import ROOT, Settings
from backend.scripts.migrate import upgrade


EXPECTED_TABLES = {
    "cases", "case_participants", "context_features", "context_items", "messages", "questions", "question_answers",
    "facts", "verifications", "verification_evidence", "tasks", "customer_progress", "ai_suggestions", "case_events",
    "case_briefs", "reports", "ai_runs", "personal_notes", "bookmarks", "attachments", "official_contacts", "idempotency_keys",
}


@pytest.fixture
def migrated_engine():
    (ROOT / ".cache").mkdir(exist_ok=True)
    with TemporaryDirectory(dir=ROOT / ".cache") as directory:
        settings = Settings(app_env="test", database_url=f"sqlite:///{Path(directory).as_posix()}/case.db")
        upgrade(settings)
        engine = create_engine(settings.database_url)
        try:
            yield engine
        finally:
            engine.dispose()


def test_schema_contains_all_v4_entities_and_no_legacy_actions(migrated_engine):
    names = set(inspect(migrated_engine).get_table_names())
    assert EXPECTED_TABLES <= names
    assert "actions" not in names
    assert "case_events" in names
    assert "alembic_version" in names


def test_cases_require_valid_status_revision_and_fingerprint(migrated_engine):
    valid = {"id": "00000000-0000-4000-8000-000000000001", "case_number": "CSR-0001", "fingerprint": "a" * 64}
    with migrated_engine.begin() as connection:
        connection.execute(text("INSERT INTO cases (id, case_number, fingerprint) VALUES (:id, :case_number, :fingerprint)"), valid)
        with pytest.raises(IntegrityError):
            connection.execute(text("INSERT INTO cases (id, case_number, fingerprint, status) VALUES ('00000000-0000-4000-8000-000000000002', 'CSR-0002', :fingerprint, 'INVALID')"), valid)
        with pytest.raises(IntegrityError):
            connection.execute(text("INSERT INTO cases (id, case_number, fingerprint, revision) VALUES ('00000000-0000-4000-8000-000000000003', 'CSR-0003', :fingerprint, 0)"), valid)


def test_case_scoped_visibility_and_idempotency_constraints(migrated_engine):
    with migrated_engine.begin() as connection:
        connection.execute(text("INSERT INTO cases (id, case_number, fingerprint) VALUES ('00000000-0000-4000-8000-000000000001', 'CSR-0001', :fingerprint)"), {"fingerprint": "a" * 64})
        with pytest.raises(IntegrityError):
            connection.execute(text("INSERT INTO messages (id, case_id, visibility, sender_role, content) VALUES ('00000000-0000-4000-8000-000000000002', '00000000-0000-4000-8000-000000000001', 'PUBLIC', 'CUSTOMER', 'x')"))
        payload = {"id": "00000000-0000-4000-8000-000000000003", "case": "00000000-0000-4000-8000-000000000001", "request": "00000000-0000-4000-8000-000000000004", "fingerprint": "b" * 64}
        connection.execute(text("INSERT INTO idempotency_keys (id, case_id, client_request_id, operation, request_fingerprint) VALUES (:id, :case, :request, 'CREATE_MESSAGE', :fingerprint)"), payload)
        with pytest.raises(IntegrityError):
            connection.execute(text("INSERT INTO idempotency_keys (id, case_id, client_request_id, operation, request_fingerprint) VALUES ('00000000-0000-4000-8000-000000000005', :case, :request, 'CREATE_MESSAGE', :fingerprint)"), payload)
