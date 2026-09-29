"""Durable, per-case leased guidance jobs (also used by the in-memory repository)."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import asyncio
from contextlib import asynccontextmanager

import aiomysql


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CopilotJobs:
    def __init__(self, repository):
        self.repo = repository
        # AsyncMock repositories are not a SQL backend.
        from .mysql_repository import MySqlCaseRepository
        self.mysql = isinstance(repository, MySqlCaseRepository)
        if not self.mysql and not isinstance(getattr(repository, "_copilot_jobs", None), dict):
            repository._copilot_jobs = {}

    @asynccontextmanager
    async def serialize(self, case_id):
        if not self.mysql:
            if not isinstance(getattr(self.repo, "_copilot_locks", None), dict):
                self.repo._copilot_locks = {}
            lock = self.repo._copilot_locks.setdefault(case_id, asyncio.Lock())
            async with lock:
                yield
            return
        from .copilot_state import digest
        pool = await self.repo._get_pool()
        name = "copilot:" + digest(case_id)[:48]
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT GET_LOCK(%s, 30)", (name,))
                locked = await cursor.fetchone()
            if not locked or locked[0] != 1:
                raise RuntimeError("COPILOT_CASE_BUSY")
            try:
                yield
            finally:
                async with connection.cursor() as cursor:
                    await cursor.execute("SELECT RELEASE_LOCK(%s)", (name,))

    async def enqueue(self, case_id, key, kind, revision, actor):
        stamp = now()
        job = dict(job_id=f"copilot-{uuid4().hex}", case_id=case_id, dedupe_key=key,
            trigger_kind=kind, source_revision=revision, actor_user_id=actor, status="PENDING",
            attempts=0, lease_token=None, lease_until=None, next_attempt_at=stamp,
            result_message_id=None, error_code=None, created_at=stamp, updated_at=stamp)
        if not self.mysql:
            return deepcopy(self.repo._copilot_jobs.setdefault((case_id, key), job))
        pool = await self.repo._get_pool()
        async with pool.acquire() as connection, connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("""INSERT IGNORE INTO case_copilot_jobs
                (job_id,case_id,dedupe_key,trigger_kind,source_revision,actor_user_id,created_at,updated_at,next_attempt_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (job["job_id"],case_id,key,kind,revision,actor,stamp,stamp,stamp))
            await cursor.execute("SELECT * FROM case_copilot_jobs WHERE case_id=%s AND dedupe_key=%s", (case_id,key))
            result = await cursor.fetchone()
            await connection.commit()
            return result

    async def claim(self, job):
        stamp, token = now(), uuid4().hex
        if not self.mysql:
            rows = self.repo._copilot_jobs
            row = rows[(job["case_id"], job["dedupe_key"])]
            if not self._eligible(row, stamp) or any(r["case_id"] == row["case_id"] and
                r["status"] == "PROCESSING" and r["lease_until"] > stamp for r in rows.values()):
                return None
            row.update(status="PROCESSING", attempts=row["attempts"]+1, lease_token=token,
                       lease_until=stamp+timedelta(minutes=15), updated_at=stamp)
            return deepcopy(row)
        pool = await self.repo._get_pool()
        async with pool.acquire() as connection:
            try:
                await connection.begin()
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute("SELECT case_id FROM cases WHERE case_id=%s FOR UPDATE", (job["case_id"],))
                    await cursor.fetchone()
                    await cursor.execute("SELECT * FROM case_copilot_jobs WHERE job_id=%s FOR UPDATE", (job["job_id"],))
                    row = await cursor.fetchone()
                    await cursor.execute("SELECT job_id FROM case_copilot_jobs WHERE case_id=%s AND status='PROCESSING' AND lease_until>%s", (job["case_id"],stamp))
                    busy = await cursor.fetchone()
                    if not row or not self._eligible(row, stamp) or busy:
                        await connection.rollback()
                        return None
                    await cursor.execute("UPDATE case_copilot_jobs SET status='PROCESSING',attempts=attempts+1,lease_token=%s,lease_until=%s,updated_at=%s WHERE job_id=%s", (token,stamp+timedelta(minutes=15),stamp,row["job_id"]))
                    row.update(status="PROCESSING", attempts=row["attempts"]+1, lease_token=token)
                await connection.commit()
                return row
            except BaseException:
                await connection.rollback()
                raise

    @staticmethod
    def _eligible(row, stamp):
        if row["status"] in {"COMPLETED", "SUPERSEDED"} or row["attempts"] >= 3:
            return False
        if row["status"] == "PROCESSING" and row.get("lease_until") and row["lease_until"] > stamp:
            return False
        return not row.get("next_attempt_at") or row["next_attempt_at"] <= stamp

    async def finish(self, job, status, message_id=None, error_code=None):
        stamp = now()
        changes = dict(status=status, result_message_id=message_id, error_code=error_code,
            lease_token=None, lease_until=None, next_attempt_at=stamp+timedelta(seconds=30*job["attempts"]), updated_at=stamp)
        if not self.mysql:
            row = self.repo._copilot_jobs[(job["case_id"],job["dedupe_key"])]
            if row["lease_token"] == job["lease_token"]:
                row.update(changes)
            return
        pool = await self.repo._get_pool()
        async with pool.acquire() as connection, connection.cursor() as cursor:
            await cursor.execute("""UPDATE case_copilot_jobs SET status=%s,result_message_id=%s,error_code=%s,
                lease_token=NULL,lease_until=NULL,next_attempt_at=%s,updated_at=%s WHERE job_id=%s AND lease_token=%s""",
                (status,message_id,error_code,changes["next_attempt_at"],stamp,job["job_id"],job["lease_token"]))
            await connection.commit()

    async def pending(self):
        if not self.mysql:
            return [deepcopy(r) for r in self.repo._copilot_jobs.values() if self._eligible(r,now())]
        pool = await self.repo._get_pool()
        async with pool.acquire() as connection, connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("""SELECT * FROM case_copilot_jobs WHERE attempts<3 AND
                (status IN ('PENDING','FAILED') OR (status='PROCESSING' AND lease_until<=UTC_TIMESTAMP(6)))
                AND (next_attempt_at IS NULL OR next_attempt_at<=UTC_TIMESTAMP(6)) ORDER BY created_at LIMIT 30""")
            return list(await cursor.fetchall())

    async def enrolled_actor(self, case_id):
        if not self.mysql:
            rows = [r for r in self.repo._copilot_jobs.values() if r['case_id'] == case_id]
            return rows[-1]['actor_user_id'] if rows else None
        pool = await self.repo._get_pool()
        async with pool.acquire() as connection, connection.cursor() as cursor:
            await cursor.execute("SELECT actor_user_id FROM case_copilot_jobs WHERE case_id=%s ORDER BY created_at DESC LIMIT 1", (case_id,))
            row = await cursor.fetchone()
            return row[0] if row else None
