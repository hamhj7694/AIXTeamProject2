"""Internal authorization projection for case assignment roles.

The public case-member contract exposes only the assignment role. Authorization
still needs an operation role, so the server derives that role deterministically
instead of accepting a second, independently editable permission field.
"""

from __future__ import annotations

from typing import Any


_ASSIGNMENT_TO_CASE_ROLE = {
    "SUPERVISOR": "CASE_OWNER",
    "MONITORING": "REVIEWER",
    "CONSULTATION": "CHAT_OPERATOR",
    "VIEWER": "VIEWER",
    "HANDOVER_PENDING": "VIEWER",
}


def case_role_for_member(member: dict[str, Any]) -> str | None:
    """Return the server-derived role used by existing authorization guards."""

    assignment_role = member.get("assignment_role")
    if assignment_role in _ASSIGNMENT_TO_CASE_ROLE:
        return _ASSIGNMENT_TO_CASE_ROLE[assignment_role]
    # Read legacy rows while the migration is being rolled out. New writes do
    # not accept or persist a caller-provided permission role.
    return member.get("role")
