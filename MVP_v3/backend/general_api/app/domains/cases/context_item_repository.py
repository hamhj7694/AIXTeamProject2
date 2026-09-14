"""Transactional MySQL storage for protected context display items.

Shares the existing repository pool. Display edits use the dedicated HTTP path
with MVP member-role checks. This is not production identity authentication.
AI proposal callers still need revision/lease validation before integration.
"""
from uuid import uuid4

import aiomysql

from .context_items import (
    ContextItem, ContextItemChange, ContextItemConflictError, apply_staff_change,
    archive_display_line, archive_position, merge_ai_proposal, restore_display_line,
)


class ContextItemRepository:
    def __init__(self, case_repository):
        self.cases = case_repository

    async def edit_section(self, case_id, section, expected_version, operation, text, actor_id):
        pool = await self.cases._get_pool()
        async with pool.acquire() as connection:
            try:
                await connection.begin()
                async with connection.cursor() as cursor:
                    await cursor.execute('SELECT context_revision FROM cases WHERE case_id=%s FOR UPDATE', (case_id,))
                    case_row = await cursor.fetchone()
                    if not case_row:
                        raise KeyError(case_id)
                    await cursor.execute("SELECT state_json FROM case_context_items WHERE case_id=%s AND section=%s AND semantic_key='display' FOR UPDATE", (case_id, section))
                    row = await cursor.fetchone()
                    before = ContextItem.model_validate_json(row[0]) if row else None
                    after = section_change(before, case_id, section, expected_version, operation, text, actor_id, int(case_row[0]))
                    await self._save(cursor, before, after, operation, actor_id)
                await connection.commit()
                return after
            except BaseException:
                await connection.rollback()
                raise

    async def list_items(self, case_id: str, *, include_deleted: bool = False) -> list[ContextItem]:
        pool = await self.cases._get_pool()
        async with pool.acquire() as connection:
            try:
                async with connection.cursor() as cursor:
                    await cursor.execute('SELECT state_json FROM case_context_items WHERE case_id=%s ORDER BY item_id', (case_id,))
                    items = [ContextItem.model_validate_json(row[0]) for row in await cursor.fetchall()]
                return [item for item in items if include_deleted or item.deleted_by is None]
            finally:
                await connection.rollback()

    async def archive_line(self, case_id, section, expected_version, remaining_text, archived_text, archive_index, actor_id):
        pool = await self.cases._get_pool()
        async with pool.acquire() as connection:
            try:
                await connection.begin()
                async with connection.cursor() as cursor:
                    await cursor.execute('SELECT case_id FROM cases WHERE case_id=%s FOR UPDATE', (case_id,))
                    if not await cursor.fetchone():
                        raise KeyError(case_id)
                    await cursor.execute("SELECT state_json FROM case_context_items WHERE case_id=%s AND section=%s AND semantic_key='display' FOR UPDATE", (case_id, section))
                    row = await cursor.fetchone()
                    before = ContextItem.model_validate_json(row[0]) if row else None
                    await cursor.execute("SELECT state_json FROM case_context_items WHERE case_id=%s AND section=%s AND semantic_key LIKE 'display-archive:%%' FOR UPDATE", (case_id, section))
                    existing_archives = [ContextItem.model_validate_json(value[0]) for value in await cursor.fetchall()]
                    archive_id = f'ctx-{uuid4().hex}'
                    display, archive = archive_display_line(
                        before, case_id=case_id, section=section, expected_version=expected_version,
                        remaining_text=remaining_text, archived_text=archived_text,
                        archive_index=archive_position(archive_index, existing_archives),
                        archive_item_id=archive_id, actor_id=actor_id,
                    )
                    await self._save(cursor, before, display, 'ARCHIVE_DELETE', actor_id)
                    await self._save(cursor, None, archive, 'ARCHIVE_DELETE', actor_id)
                await connection.commit()
                return display, archive
            except BaseException:
                await connection.rollback()
                raise

    async def restore_archive(self, case_id, section, expected_version, archive_item_id, archive_version, actor_id):
        pool = await self.cases._get_pool()
        async with pool.acquire() as connection:
            try:
                await connection.begin()
                async with connection.cursor() as cursor:
                    await cursor.execute("SELECT state_json FROM case_context_items WHERE case_id=%s AND section=%s AND semantic_key='display' FOR UPDATE", (case_id, section))
                    display_row = await cursor.fetchone()
                    await cursor.execute("SELECT state_json FROM case_context_items WHERE case_id=%s AND section=%s AND semantic_key LIKE 'display-archive:%%' FOR UPDATE", (case_id, section))
                    archives = [ContextItem.model_validate_json(value[0]) for value in await cursor.fetchall()]
                    before_archive = next((item for item in archives if item.item_id == archive_item_id), None)
                    if not display_row or before_archive is None:
                        raise KeyError(archive_item_id)
                    before_display = ContextItem.model_validate_json(display_row[0])
                    archived_before = sum(1 for item in archives if item.deleted_by is not None and item.archive_index is not None
                                          and before_archive.archive_index is not None and item.archive_index < before_archive.archive_index)
                    display, archive = restore_display_line(
                        before_display, before_archive, expected_version=expected_version,
                        archive_version=archive_version, actor_id=actor_id,
                        archived_before=archived_before,
                    )
                    await self._save(cursor, before_display, display, 'RESTORE_ARCHIVE', actor_id)
                    await self._save(cursor, before_archive, archive, 'RESTORE_ARCHIVE', actor_id)
                await connection.commit()
                return display, archive
            except BaseException:
                await connection.rollback()
                raise

    async def propose(self, case_id: str, section: str, semantic_key: str, text: str, evidence_refs: list[str]) -> ContextItem:
        # Validate before opening a transaction. Keys must derive from evidence
        # identity/field/purpose, never text hashes or presentation array indexes.
        seed = ContextItem(item_id=f'ctx-{uuid4().hex}', case_id=case_id,
                           section=section, semantic_key=semantic_key, item_version=1)
        validated = merge_ai_proposal(seed, text, evidence_refs).model_copy(update={'item_version': 1})
        pool = await self.cases._get_pool()
        async with pool.acquire() as connection:
            try:
                await connection.begin()
                async with connection.cursor() as cursor:
                    # Parent lock serializes first insert for the same Case/key.
                    await cursor.execute('SELECT case_id FROM cases WHERE case_id=%s FOR UPDATE', (case_id,))
                    if not await cursor.fetchone():
                        raise KeyError(case_id)
                    await cursor.execute('SELECT state_json FROM case_context_items WHERE case_id=%s AND section=%s AND semantic_key=%s FOR UPDATE', (case_id, section, semantic_key))
                    row = await cursor.fetchone()
                    before = ContextItem.model_validate_json(row[0]) if row else None
                    after = merge_ai_proposal(before, text, evidence_refs) if before else validated
                    await self._save(cursor, before, after, 'AI_PROPOSAL', 'system:context-ai')
                await connection.commit()
                return after
            except BaseException:
                await connection.rollback()
                raise

    async def change(self, case_id: str, item_id: str, change: ContextItemChange, actor_id: str) -> ContextItem:
        pool = await self.cases._get_pool()
        async with pool.acquire() as connection:
            try:
                await connection.begin()
                async with connection.cursor() as cursor:
                    await cursor.execute('SELECT state_json FROM case_context_items WHERE case_id=%s AND item_id=%s FOR UPDATE', (case_id, item_id))
                    row = await cursor.fetchone()
                    if not row:
                        raise KeyError(item_id)
                    before = ContextItem.model_validate_json(row[0])
                    after = apply_staff_change(before, change, actor_id)
                    await self._save(cursor, before, after, change.operation, actor_id)
                await connection.commit()
                return after
            except BaseException:
                await connection.rollback()
                raise

    @staticmethod
    async def _save(cursor, before, after, operation, actor_id):
        if before == after:
            return
        payload = after.model_dump_json()
        if before is None:
            await cursor.execute('INSERT INTO case_context_items (item_id,case_id,section,semantic_key,item_version,state_json) VALUES (%s,%s,%s,%s,%s,%s)',
                                 (after.item_id, after.case_id, after.section, after.semantic_key, after.item_version, payload))
        else:
            await cursor.execute('UPDATE case_context_items SET item_version=%s,state_json=%s,updated_at=CURRENT_TIMESTAMP(6) WHERE item_id=%s AND case_id=%s',
                                 (after.item_version, payload, after.item_id, after.case_id))
        await cursor.execute('INSERT INTO case_context_item_history (item_id,item_version,operation,actor_id,before_json,after_json) VALUES (%s,%s,%s,%s,%s,%s)',
                             (after.item_id, after.item_version, operation, actor_id, before.model_dump_json() if before else None, payload))


def section_change(before, case_id, section, version, operation, text, actor_id, base_projection_revision=None):
    if version != (before.item_version if before else 0):
        raise ContextItemConflictError('다른 담당자가 수정했습니다. 최신 내용을 다시 확인해 주세요.')
    seed = before or ContextItem(item_id=f'ctx-{uuid4().hex}', case_id=case_id, section=section, semantic_key='display', item_version=1)
    change = ContextItemChange(expected_version=seed.item_version, operation=operation, text=text)
    result = apply_staff_change(seed, change, actor_id)
    if operation == 'EDIT' and base_projection_revision is not None:
        result = result.model_copy(update={'base_projection_revision': base_projection_revision})
    return result if before else result.model_copy(update={'item_version': 1})


class InMemoryContextItemRepository:
    """Test implementation using the owning Case repository's lock."""
    def __init__(self, cases):
        self.cases = cases
        if not hasattr(cases, '_display_items'):
            cases._display_items = {}

    async def list_items(self, case_id, *, include_deleted=False):
        return [item for (cid, _), item in self.cases._display_items.items() if cid == case_id and (include_deleted or not item.deleted_by)]

    async def edit_section(self, case_id, section, expected_version, operation, text, actor_id):
        async with self.cases._lock:
            before = self.cases._display_items.get((case_id, section))
            case = await self.cases.get(case_id)
            if case is None:
                raise KeyError(case_id)
            result = section_change(before, case_id, section, expected_version, operation, text, actor_id, int(case.get('context_revision', 1)))
            self.cases._display_items[(case_id, section)] = result
            return result

    async def archive_line(self, case_id, section, expected_version, remaining_text, archived_text, archive_index, actor_id):
        async with self.cases._lock:
            before = self.cases._display_items.get((case_id, section))
            existing_archives = [item for (cid, _), item in self.cases._display_items.items()
                                 if cid == case_id and item.section == section and item.semantic_key.startswith('display-archive:')]
            archive_id = f'ctx-{uuid4().hex}'
            display, archive = archive_display_line(
                before, case_id=case_id, section=section, expected_version=expected_version,
                remaining_text=remaining_text, archived_text=archived_text,
                archive_index=archive_position(archive_index, existing_archives),
                archive_item_id=archive_id, actor_id=actor_id,
            )
            self.cases._display_items[(case_id, section)] = display
            self.cases._display_items[(case_id, archive.item_id)] = archive
            return display, archive

    async def restore_archive(self, case_id, section, expected_version, archive_item_id, archive_version, actor_id):
        async with self.cases._lock:
            display = self.cases._display_items.get((case_id, section))
            archive = self.cases._display_items.get((case_id, archive_item_id))
            if display is None or archive is None:
                raise KeyError(archive_item_id)
            archives = [item for (cid, _), item in self.cases._display_items.items()
                        if cid == case_id and item.section == section and item.semantic_key.startswith('display-archive:')]
            archived_before = sum(1 for item in archives if item.deleted_by is not None and item.archive_index is not None
                                  and archive.archive_index is not None and item.archive_index < archive.archive_index)
            restored_display, restored_archive = restore_display_line(
                display, archive, expected_version=expected_version,
                archive_version=archive_version, actor_id=actor_id,
                archived_before=archived_before,
            )
            self.cases._display_items[(case_id, section)] = restored_display
            self.cases._display_items[(case_id, archive_item_id)] = restored_archive
            return restored_display, restored_archive
