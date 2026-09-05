"""Durable, revision-checked single-flight storage for Case Context output."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

import aiomysql


ClaimOutcome = Literal['CLAIMED', 'CACHED', 'IN_PROGRESS', 'STALE']
CASE_SUPPORT_SCHEMA_VERSION = 'case-support.v3'


@dataclass(frozen=True)
class ProjectionClaim:
    outcome: ClaimOutcome
    current_revision: int
    lease_token: str | None = None
    last_success_revision: int | None = None
    last_success_payload: dict[str, Any] | None = None


class ContextProjectionRepository:
    """Uses the Case repository pool; callers invoke AI only after CLAIMED."""

    def __init__(self, case_repository) -> None:
        self.cases = case_repository

    @staticmethod
    def _json(value: Any) -> dict[str, Any] | None:
        if value is None or isinstance(value, dict):
            return value
        if isinstance(value, (bytes, bytearray)):
            value = value.decode('utf-8')
        return json.loads(value)

    async def get_revision(self, case_id: str) -> int:
        pool = await self.cases._get_pool()
        async with pool.acquire() as connection, connection.cursor() as cursor:
            try:
                await cursor.execute('SELECT context_revision FROM cases WHERE case_id=%s AND deleted_at IS NULL', (case_id,))
                row = await cursor.fetchone()
                if not row:
                    raise KeyError(case_id)
                return int(row[0])
            finally:
                await connection.rollback()

    async def claim(self, case_id: str, requested_revision: int, *, lease_seconds: int = 45) -> ProjectionClaim:
        if requested_revision < 1 or not 5 <= lease_seconds <= 300:
            raise ValueError('유효하지 않은 revision 또는 lease 시간입니다.')
        pool = await self.cases._get_pool()
        now = datetime.now()
        token = uuid4().hex
        async with pool.acquire() as connection:
            try:
                await connection.begin()
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute('SELECT context_revision FROM cases WHERE case_id=%s AND deleted_at IS NULL FOR UPDATE', (case_id,))
                    case = await cursor.fetchone()
                    if not case:
                        raise KeyError(case_id)
                    current = int(case['context_revision'])
                    await cursor.execute('SELECT * FROM case_context_projections WHERE case_id=%s FOR UPDATE', (case_id,))
                    row = await cursor.fetchone()
                    payload = self._json(row.get('last_success_payload')) if row else None
                    success_revision = int(row['last_success_revision']) if row and row.get('last_success_revision') is not None else None
                    if current != requested_revision:
                        await connection.commit()
                        return ProjectionClaim('STALE', current, last_success_revision=success_revision, last_success_payload=payload)
                    if success_revision == current and payload is not None and row.get('schema_version') == CASE_SUPPORT_SCHEMA_VERSION:
                        await connection.commit()
                        return ProjectionClaim('CACHED', current, last_success_revision=success_revision, last_success_payload=payload)
                    if row and row.get('generating_revision') == current and row.get('lease_expires_at') and row['lease_expires_at'] > now:
                        await connection.commit()
                        return ProjectionClaim('IN_PROGRESS', current, last_success_revision=success_revision, last_success_payload=payload)
                    expires = now + timedelta(seconds=lease_seconds)
                    if row:
                        await cursor.execute(
                            """UPDATE case_context_projections SET generation_status='GENERATING',generating_revision=%s,
                               lease_token=%s,lease_expires_at=%s,last_error=NULL,updated_at=%s WHERE case_id=%s""",
                            (current, token, expires, now, case_id),
                        )
                    else:
                        await cursor.execute(
                            """INSERT INTO case_context_projections
                               (case_id,generation_status,generating_revision,lease_token,lease_expires_at,updated_at)
                               VALUES (%s,'GENERATING',%s,%s,%s,%s)""",
                            (case_id, current, token, expires, now),
                        )
                await connection.commit()
                return ProjectionClaim('CLAIMED', current, token, success_revision, payload)
            except BaseException:
                await connection.rollback()
                raise

    async def complete(self, case_id: str, revision: int, lease_token: str, payload: dict[str, Any], *,
                       schema_version: str = CASE_SUPPORT_SCHEMA_VERSION, model_version: str | None = None,
                       prompt_version: str | None = None) -> bool:
        encoded = json.dumps(payload, ensure_ascii=False)
        now = datetime.now()
        pool = await self.cases._get_pool()
        async with pool.acquire() as connection:
            try:
                await connection.begin()
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute('SELECT context_revision FROM cases WHERE case_id=%s AND deleted_at IS NULL FOR UPDATE', (case_id,))
                    case = await cursor.fetchone()
                    await cursor.execute('SELECT generating_revision,lease_token FROM case_context_projections WHERE case_id=%s FOR UPDATE', (case_id,))
                    row = await cursor.fetchone()
                    valid = bool(case and row and int(case['context_revision']) == revision
                                 and row['generating_revision'] == revision and row['lease_token'] == lease_token)
                    if not valid:
                        await connection.commit()
                        return False
                    await cursor.execute(
                        """UPDATE case_context_projections SET generation_status='CURRENT',generating_revision=NULL,
                           lease_token=NULL,lease_expires_at=NULL,last_success_revision=%s,last_success_payload=%s,
                           schema_version=%s,model_version=%s,prompt_version=%s,last_error=NULL,generated_at=%s,updated_at=%s
                           WHERE case_id=%s""",
                        (revision, encoded, schema_version, model_version, prompt_version, now, now, case_id),
                    )
                await connection.commit()
                return True
            except BaseException:
                await connection.rollback()
                raise

    async def fail(self, case_id: str, revision: int, lease_token: str, safe_error: str) -> bool:
        """Keep last success. safe_error must not contain prompts, messages or secrets."""
        message = ' '.join(safe_error.split())[:500] or 'AI_CONTEXT_GENERATION_FAILED'
        pool = await self.cases._get_pool()
        now = datetime.now()
        async with pool.acquire() as connection:
            try:
                async with connection.cursor() as cursor:
                    await cursor.execute(
                        """UPDATE case_context_projections SET
                           generation_status=IF(last_success_payload IS NULL,'FAILED','STALE'),
                           generating_revision=NULL,lease_token=NULL,lease_expires_at=NULL,last_error=%s,updated_at=%s
                           WHERE case_id=%s AND generating_revision=%s AND lease_token=%s""",
                        (message, now, case_id, revision, lease_token),
                    )
                    changed = cursor.rowcount == 1
                await connection.commit()
                return changed
            except BaseException:
                await connection.rollback()
                raise

    async def read(self, case_id: str) -> dict[str, Any] | None:
        pool = await self.cases._get_pool()
        async with pool.acquire() as connection, connection.cursor(aiomysql.DictCursor) as cursor:
            try:
                await cursor.execute('SELECT * FROM case_context_projections WHERE case_id=%s', (case_id,))
                row = await cursor.fetchone()
                if not row:
                    return None
                return {**row, 'last_success_payload': self._json(row.get('last_success_payload'))}
            finally:
                await connection.rollback()
