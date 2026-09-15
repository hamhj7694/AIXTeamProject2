"""Actor normalization and operation authorization primitives.

This module is intentionally framework-agnostic so route handlers can adopt it
without changing the current query-parameter based API in one step.
"""

from dataclasses import dataclass
from typing import Iterable, Literal

ActorType = Literal["BANK_STAFF", "CUSTOMER", "AI_AGENT", "SYSTEM"]
CaseRole = Literal["CASE_OWNER", "CHAT_OPERATOR", "REVIEWER", "VIEWER", "CUSTOMER"]

_READ = {"CASE_OWNER", "CHAT_OPERATOR", "REVIEWER", "VIEWER"}
_WRITE = {"CASE_OWNER", "CHAT_OPERATOR", "REVIEWER"}
_REVIEW = {"CASE_OWNER", "REVIEWER"}


@dataclass(frozen=True)
class ActorContext:
    actor_id: str
    actor_type: ActorType
    case_role: CaseRole | None = None
    display_name: str | None = None
    auth_source: Literal["SESSION", "SERVICE_TOKEN", "MVP_DEMO"] = "MVP_DEMO"
    case_id: str | None = None

    @property
    def permissions(self) -> frozenset[str]:
        return frozenset(operation for operation in ("READ", "WRITE", "REVIEW") if self.can(operation))

    def can(self, operation: Literal["READ", "WRITE", "REVIEW"]) -> bool:
        if self.actor_type in {"AI_AGENT", "SYSTEM"}:
            return self.auth_source == "SERVICE_TOKEN"
        if self.actor_type == "CUSTOMER":
            return operation == "READ" and self.case_role == "CUSTOMER"
        role = self.case_role
        return role in {"READ": _READ, "WRITE": _WRITE, "REVIEW": _REVIEW}[operation]

    def for_case(self, case_id: str, role: str) -> "ActorContext":
        valid_roles = {"CASE_OWNER", "CHAT_OPERATOR", "REVIEWER", "VIEWER", "CUSTOMER"}
        resolved_role: CaseRole | None = role if role in valid_roles else None  # type: ignore[assignment]
        return ActorContext(
            actor_id=self.actor_id,
            actor_type=self.actor_type,
            case_role=resolved_role,
            display_name=self.display_name,
            auth_source=self.auth_source,
            case_id=case_id,
        )


def normalize_legacy_actor(
    actor_user_id: str,
    *,
    role: str | None = None,
    actor_type: str | None = None,
    display_name: str | None = None,
    auth_source: str = "MVP_DEMO",
) -> ActorContext:
    """Convert current query/body actor fields into a trusted internal shape.

    `actor_type` is accepted for compatibility but cannot elevate permissions;
    callers should derive the role from case membership before authorization.
    """
    actor_id = (actor_user_id or "").strip()
    if not actor_id:
        raise ValueError("actor_user_id is required")
    lowered = actor_id.lower()
    requested_type = (actor_type or "").upper()
    if lowered in {"case-copilot", "customer-agent", "ai", "system:context-ai"} or requested_type == "AI_AGENT":
        resolved_type: ActorType = "AI_AGENT"
    elif lowered.startswith("system:") or requested_type == "SYSTEM":
        resolved_type = "SYSTEM"
    elif requested_type == "CUSTOMER" or lowered == "customer":
        resolved_type = "CUSTOMER"
    else:
        resolved_type = "BANK_STAFF"
    valid_roles = {"CASE_OWNER", "CHAT_OPERATOR", "REVIEWER", "VIEWER", "CUSTOMER"}
    # A claimed actor type never grants a case role. Routes must bind the role
    # from an active case membership through ``for_case`` before authorization.
    resolved_role = role if role in valid_roles else None
    source = auth_source if auth_source in {"SESSION", "SERVICE_TOKEN", "MVP_DEMO"} else "MVP_DEMO"
    return ActorContext(
        actor_id=actor_id,
        actor_type=resolved_type,
        case_role=resolved_role,
        display_name=display_name,
        auth_source=source,
    )


def permissions_for(actor: ActorContext) -> frozenset[str]:
    return actor.permissions
