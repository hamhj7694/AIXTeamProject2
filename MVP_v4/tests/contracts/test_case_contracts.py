from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.contracts.case import (
    ActorRole, CaseEvent, CaseMode, CaseStatus, EntityType, LossStatus, SharedCase,
    StructuredFeaturePayload, Visibility, WritePrecondition,
)


def fingerprint() -> str:
    return "a" * 64


def test_shared_case_contract_has_single_revision_and_version_boundary():
    case = SharedCase(
        id=uuid4(), status=CaseStatus.TRIAGE, mode=CaseMode.PREVENT, loss_status=LossStatus.UNKNOWN,
        revision=1, fingerprint=fingerprint(), version=1, created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    )
    assert case.revision == case.version == 1
    with pytest.raises(ValidationError):
        SharedCase.model_validate({**case.model_dump(), "revision": 0})
    with pytest.raises(ValidationError):
        SharedCase.model_validate({**case.model_dump(), "fingerprint": "not-a-fingerprint"})


def test_write_precondition_requires_uuid_and_rejects_invalid_version():
    assert WritePrecondition(client_request_id=uuid4(), expected_version=3).expected_version == 3
    with pytest.raises(ValidationError):
        WritePrecondition(client_request_id="not-a-uuid")
    with pytest.raises(ValidationError):
        WritePrecondition(client_request_id=uuid4(), expected_version=0)


def test_case_event_contract_carries_server_enforced_visibility_and_revision():
    event = CaseEvent(
        id=uuid4(), case_id=uuid4(), event_type="ENTITY_CREATED", entity_type=EntityType.TASK,
        actor_role=ActorRole.BANK_STAFF, visibility=Visibility.BANK_INTERNAL, case_revision=2,
        payload={"status": "TODO"}, created_at=datetime.now(UTC),
    )
    assert event.visibility == Visibility.BANK_INTERNAL
    with pytest.raises(ValidationError):
        CaseEvent.model_validate({**event.model_dump(), "visibility": "PUBLIC"})


@pytest.mark.parametrize("payload", [
    {"raw_text": "call transcript"}, {"nested": {"transcript": "call transcript"}},
    {"items": [{"source_text": "call transcript"}]},
])
def test_feature_contract_rejects_source_text(payload):
    with pytest.raises(ValidationError, match="source text"):
        StructuredFeaturePayload(schema_version="v1", values=payload)


def test_feature_contract_allows_structured_values_only():
    item = StructuredFeaturePayload(schema_version="v1", values={"risk": 0.91, "signals": ["MONEY_MOVEMENT"]})
    assert item.values["risk"] == 0.91
