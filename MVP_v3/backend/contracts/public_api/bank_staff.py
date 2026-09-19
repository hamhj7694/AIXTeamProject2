"""Public contract for the bank-wide staff directory."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


StaffColor = Literal["GREEN", "BLUE", "YELLOW", "ORANGE", "RED", "PURPLE", "GRAY"]
StaffAssignmentRole = Literal["SUPERVISOR", "MONITORING", "CONSULTATION", "OTHER_VIEWER", "HANDOVER_PENDING"]


class PublicBankStaffBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=100)
    assignment_role: StaffAssignmentRole = "CONSULTATION"
    role_label: str = Field(min_length=1, max_length=100)
    position_title: str | None = Field(default=None, max_length=100)
    status_text: str = Field(default="근무 중", min_length=1, max_length=80)
    status_color_key: StaffColor = "GREEN"
    assignment_eligible: bool = True
    linked_user_id: str | None = Field(default=None, max_length=64)


class PublicBankStaffCreateRequest(PublicBankStaffBase):
    pass


class PublicBankStaffUpdateRequest(PublicBankStaffBase):
    pass


class PublicBankStaffResponse(PublicBankStaffBase):
    staff_id: str
    is_self: bool = False
    created_at: str
    updated_at: str
