"""Context display overlays, not a second store of confirmed facts or actions.

Display endpoints check the Case member role under the existing MVP identity
model. An actor ID supplied by a client is not production authentication.
"""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


Section = Literal['SUMMARY', 'SIGNAL', 'CLAIM', 'DEMAND', 'TACTIC', 'NEXT_STEP', 'EXPOSURE']


class ContextItemConflictError(Exception):
    """Map to HTTP 409 at the eventual authenticated API boundary."""


class ContextItem(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    item_id: str
    case_id: str
    section: Section
    semantic_key: str = Field(min_length=1, max_length=160, pattern=r'^[a-zA-Z0-9_.:/-]+$')
    item_version: int = Field(ge=1)
    ai_text: str | None = None
    staff_text: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    edited_by: str | None = None
    deleted_by: str | None = None

    @property
    def effective_text(self) -> str:
        return self.staff_text if self.staff_text is not None else self.ai_text or ''


class ContextItemChange(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=1)
    operation: Literal['EDIT', 'DELETE', 'RESTORE', 'RESET']
    text: str | None = Field(default=None, min_length=1, max_length=4000)

    @model_validator(mode='after')
    def validate_operation(self):
        if self.operation == 'EDIT':
            if self.text is None or not self.text.strip():
                raise ValueError('편집 내용이 필요합니다.')
        elif self.text is not None:
            raise ValueError('삭제·복원 시 본문을 변경할 수 없습니다.')
        return self


def apply_staff_change(item: ContextItem, change: ContextItemChange, actor_id: str) -> ContextItem:
    if not actor_id.strip() or len(actor_id) > 64:
        raise ValueError('유효한 서버 확인 사용자 ID가 필요합니다.')
    if change.expected_version != item.item_version:
        raise ContextItemConflictError('항목이 변경되었습니다. 최신 내용을 확인해 주세요.')
    if change.operation == 'EDIT' and item.deleted_by is not None:
        raise ContextItemConflictError('삭제된 항목은 복원한 뒤 수정해 주세요.')
    changes: dict = {}
    if change.operation == 'EDIT':
        changes = {'staff_text': change.text.strip(), 'edited_by': actor_id}
    elif change.operation == 'DELETE' and item.deleted_by is None:
        changes = {'deleted_by': actor_id}
    elif change.operation == 'RESTORE' and item.deleted_by is not None:
        changes = {'deleted_by': None}
    elif change.operation == 'RESET':
        changes = {'staff_text': None, 'edited_by': None, 'deleted_by': None}
    if not changes:
        return item
    return item.model_copy(update={**changes, 'item_version': item.item_version + 1})


def merge_ai_proposal(item: ContextItem, text: str, evidence_refs: list[str]) -> ContextItem:
    """Preserve employee wording AND tombstone when AI rephrases the same key."""
    if not text.strip() or len(text) > 4000:
        raise ValueError('AI 항목 본문 길이가 유효하지 않습니다.')
    refs = list(dict.fromkeys(evidence_refs))
    if item.ai_text == text.strip() and item.evidence_refs == refs:
        return item
    return item.model_copy(update={
        'ai_text': text.strip(), 'evidence_refs': refs,
        'item_version': item.item_version + 1,
    })
