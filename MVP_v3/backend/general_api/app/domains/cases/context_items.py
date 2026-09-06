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
    archive_index: int | None = Field(default=None, ge=0)

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


def archive_display_line(
    item: ContextItem | None,
    *,
    case_id: str,
    section: Section,
    expected_version: int,
    remaining_text: str | None,
    archived_text: str,
    archive_index: int,
    archive_item_id: str,
    actor_id: str,
) -> tuple[ContextItem, ContextItem]:
    if not actor_id.strip() or len(actor_id) > 64:
        raise ValueError('유효한 서버 확인 사용자 ID가 필요합니다.')
    if expected_version != (item.item_version if item else 0):
        raise ContextItemConflictError('다른 담당자가 수정했습니다. 최신 내용을 다시 확인해 주세요.')
    if item is not None and item.deleted_by is not None:
        raise ContextItemConflictError('이미 비어 있는 영역에서는 항목을 삭제할 수 없습니다.')
    archived = archived_text.strip()
    remaining = remaining_text.strip() if remaining_text else ''
    if not archived or len(archived) > 4000 or len(remaining) > 4000:
        raise ValueError('보관할 사건 맥락 내용이 유효하지 않습니다.')
    seed = item or ContextItem(
        item_id=f'ctx-{archive_item_id}', case_id=case_id, section=section,
        semantic_key='display', item_version=1,
    )
    display = seed.model_copy(update={
        'staff_text': remaining or None,
        'edited_by': actor_id,
        'deleted_by': None if remaining else actor_id,
        'item_version': item.item_version + 1 if item else 1,
    })
    archive = ContextItem(
        item_id=archive_item_id,
        case_id=case_id,
        section=section,
        semantic_key=f'display-archive:{archive_item_id}',
        item_version=1,
        staff_text=archived,
        edited_by=actor_id,
        deleted_by=actor_id,
        archive_index=archive_index,
    )
    return display, archive


def archive_position(active_index: int, archives: list[ContextItem]) -> int:
    position = active_index
    for archived_index in sorted(
        item.archive_index for item in archives
        if item.deleted_by is not None and item.archive_index is not None
    ):
        if archived_index <= position:
            position += 1
    return position


def restore_display_line(
    display: ContextItem,
    archive: ContextItem,
    *,
    expected_version: int,
    archive_version: int,
    actor_id: str,
    archived_before: int = 0,
) -> tuple[ContextItem, ContextItem]:
    if not actor_id.strip() or len(actor_id) > 64:
        raise ValueError('유효한 서버 확인 사용자 ID가 필요합니다.')
    if display.item_version != expected_version or archive.item_version != archive_version:
        raise ContextItemConflictError('다른 담당자가 수정했습니다. 최신 내용을 다시 확인해 주세요.')
    if (
        archive.case_id != display.case_id
        or archive.section != display.section
        or not archive.semantic_key.startswith('display-archive:')
        or archive.deleted_by is None
        or not archive.effective_text.strip()
    ):
        raise ContextItemConflictError('복원할 삭제 항목을 찾을 수 없습니다.')
    lines = [] if display.deleted_by is not None else [line for line in display.effective_text.splitlines() if line.strip()]
    original_index = archive.archive_index if archive.archive_index is not None else len(lines)
    index = min(max(0, original_index - archived_before), len(lines))
    lines.insert(index, archive.effective_text.strip())
    restored_display = display.model_copy(update={
        'staff_text': '\n'.join(lines),
        'edited_by': actor_id,
        'deleted_by': None,
        'item_version': display.item_version + 1,
    })
    restored_archive = archive.model_copy(update={
        'edited_by': actor_id,
        'deleted_by': None,
        'item_version': archive.item_version + 1,
    })
    return restored_display, restored_archive


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
