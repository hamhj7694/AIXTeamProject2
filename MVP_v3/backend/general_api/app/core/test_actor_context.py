import pytest

from general_api.app.core.actor_context import normalize_legacy_actor, permissions_for


def test_bank_reviewer_permissions():
    actor = normalize_legacy_actor("staff-1", role="REVIEWER")
    assert permissions_for(actor) == {"READ", "WRITE", "REVIEW"}


def test_viewer_cannot_write():
    actor = normalize_legacy_actor("staff-1", role="VIEWER")
    assert actor.can("READ")
    assert not actor.can("WRITE")


def test_client_actor_type_cannot_escalate():
    actor = normalize_legacy_actor("staff-1", role="VIEWER", actor_type="REVIEWER")
    assert not actor.can("REVIEW")


def test_ai_requires_service_token():
    demo = normalize_legacy_actor("case-copilot")
    service = normalize_legacy_actor("case-copilot", auth_source="SERVICE_TOKEN")
    assert not demo.can("WRITE")
    assert service.can("WRITE")


def test_customer_is_read_only_inside_its_case():
    actor = normalize_legacy_actor("customer-1", actor_type="CUSTOMER").for_case("case-1", "CUSTOMER")
    assert actor.case_id == "case-1"
    assert actor.permissions == {"READ"}


def test_bank_owner_gets_case_scoped_permissions():
    actor = normalize_legacy_actor("staff-1").for_case("case-1", "CASE_OWNER")
    assert actor.actor_type == "BANK_STAFF"
    assert actor.permissions == {"READ", "WRITE", "REVIEW"}


def test_empty_actor_is_invalid():
    with pytest.raises(ValueError, match="actor_user_id is required"):
        normalize_legacy_actor("  ")


def test_system_actor_is_not_a_human_demo_user():
    system = normalize_legacy_actor("system:projection")
    assert system.actor_type == "SYSTEM"
    assert system.permissions == set()


def test_customer_agent_is_not_treated_as_customer_or_staff():
    agent = normalize_legacy_actor("customer-agent", actor_type="CUSTOMER")
    assert agent.actor_type == "AI_AGENT"
    assert agent.permissions == set()
