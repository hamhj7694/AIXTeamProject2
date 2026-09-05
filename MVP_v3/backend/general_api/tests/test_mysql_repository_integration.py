from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pymysql
import aiomysql

from ai_api.app.domains.diagnosis import DiagnosisService
from ai_api.app.domains.diagnosis.extractor import EventExtraction, _local_safety_events, parse_turns
from contracts.diagnosis import CaseContextFeatures, ContextResult
from general_api.app.domains.cases.initial_report import InitialReportBuilder
from general_api.app.domains.cases.case_context_v2_repository import (
    ContextV2ConflictError,
    ContextV2TransitionError,
    MySqlCaseContextV2Repository,
)
from general_api.app.domains.cases.mysql_repository import MySqlCaseRepository
from general_api.app.main import build_repository


BACKEND_DIR = Path(__file__).resolve().parents[2]


def mysql_test_environment(database: str) -> dict[str, str]:
    required = ("MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD")
    if not all(os.getenv(key) for key in required):
        raise unittest.SkipTest("MySQL 통합 테스트 환경변수가 설정되지 않았습니다.")
    environment = os.environ.copy()
    environment.update({
        "MYSQL_DATABASE": database,
        "CASE_REPOSITORY": "mysql",
    })
    return environment


class MySqlCaseRepositoryIntegrationTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.database = f"aix_case_platform_a0_test_{uuid4().hex[:12]}"
        cls.environment = mysql_test_environment(cls.database)
        for _ in range(2):
            subprocess.run(
                [sys.executable, "scripts/apply_migrations.py"],
                cwd=BACKEND_DIR,
                env=cls.environment,
                check=True,
                capture_output=True,
                text=True,
            )

    @classmethod
    def tearDownClass(cls) -> None:
        connection = pymysql.connect(
            host=cls.environment["MYSQL_HOST"],
            port=int(cls.environment.get("MYSQL_PORT", "3306")),
            user=cls.environment["MYSQL_USER"],
            password=cls.environment["MYSQL_PASSWORD"],
            autocommit=True,
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"DROP DATABASE IF EXISTS `{cls.database}`")
        finally:
            connection.close()

    async def asyncSetUp(self) -> None:
        self.environment_patch = patch.dict(os.environ, self.environment, clear=False)
        self.environment_patch.start()
        self.repository = MySqlCaseRepository()
        self.case_ids: list[str] = []

    async def asyncTearDown(self) -> None:
        try:
            await self._delete_created_cases()
        finally:
            await self.repository.close()
            self.environment_patch.stop()

    async def _delete_created_cases(self) -> None:
        if not self.case_ids:
            return
        connection = pymysql.connect(
            host=self.environment["MYSQL_HOST"],
            port=int(self.environment.get("MYSQL_PORT", "3306")),
            user=self.environment["MYSQL_USER"],
            password=self.environment["MYSQL_PASSWORD"],
            database=self.database,
            autocommit=False,
        )
        try:
            with connection.cursor() as cursor:
                placeholders = ",".join(["%s"] * len(self.case_ids))
                cursor.execute(
                    f"DELETE FROM case_report_sections WHERE report_id IN "
                    f"(SELECT report_id FROM case_reports WHERE case_id IN ({placeholders}))",
                    self.case_ids,
                )
                cursor.execute(f"DELETE FROM case_context_item_history WHERE item_id IN (SELECT item_id FROM case_context_items WHERE case_id IN ({placeholders}))", self.case_ids)
                for table in ("case_context_v2_history", "case_decisions", "case_tasks", "case_ai_suggestions", "case_gaps", "case_context_facts_v2", "case_context_items", "case_context_projections", "personal_notes", "case_facts", "customer_questions", "case_presence", "case_members", "messages", "verification_tasks", "actions", "context_features", "analysis_segments", "case_inputs", "case_events", "case_reports"):
                    cursor.execute(f"DELETE FROM {table} WHERE case_id IN ({placeholders})", self.case_ids)
                cursor.execute(f"DELETE FROM cases WHERE case_id IN ({placeholders})", self.case_ids)
            connection.commit()
        finally:
            connection.close()

    async def test_migrations_create_expected_core_schema(self) -> None:
        connection = pymysql.connect(
            host=self.environment["MYSQL_HOST"],
            port=int(self.environment.get("MYSQL_PORT", "3306")),
            user=self.environment["MYSQL_USER"],
            password=self.environment["MYSQL_PASSWORD"],
            database=self.database,
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                self.assertEqual(
                    {row[0] for row in cursor.fetchall()},
                    {
                        "actions", "analysis_segments", "case_attachments", "case_events", "case_facts", "case_inputs",
                        "case_members", "case_presence", "case_report_sections", "case_reports", "cases", "context_features",
                        "customer_questions", "message_attachments", "messages", "personal_notes", "schema_migrations",
                        "transcript_segments", "verification_tasks", "voice_sessions", "case_context_items",
                        "case_context_item_history", "case_context_projections", "case_context_facts_v2",
                        "case_gaps", "case_ai_suggestions", "case_tasks", "case_decisions", "case_context_v2_history",
                    },
                )
                cursor.execute(
                    """SELECT NUMERIC_PRECISION, NUMERIC_SCALE
                       FROM information_schema.columns
                       WHERE table_schema=%s AND table_name='cases' AND column_name='risk_score'""",
                    (self.database,),
                )
                self.assertEqual(cursor.fetchone(), (9, 6))
                cursor.execute("SELECT COLUMN_DEFAULT FROM information_schema.columns WHERE table_schema=%s AND table_name='cases' AND column_name='context_revision'", (self.database,))
                self.assertEqual(int(cursor.fetchone()[0]), 1)
                cursor.execute(
                    """SELECT COUNT(*) FROM information_schema.table_constraints
                       WHERE table_schema=%s AND constraint_type='CHECK'
                         AND table_name IN ('case_context_facts_v2','case_gaps','case_ai_suggestions','case_tasks','case_decisions')""",
                    (self.database,),
                )
                self.assertGreaterEqual(cursor.fetchone()[0], 16)
        finally:
            connection.close()

    async def test_case_context_v2_database_invariants_and_revision(self) -> None:
        case_id = f"VP-{uuid4().hex[:12]}"
        await self.repository.create(await self._record(case_id=case_id, client_request_id=uuid4().hex))
        self.case_ids.append(case_id)
        pool = await self.repository._get_pool()
        async with pool.acquire() as connection:
            try:
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute("SELECT context_revision FROM cases WHERE case_id=%s", (case_id,))
                    initial_revision = int((await cursor.fetchone())["context_revision"])

                    with self.assertRaises(pymysql.err.OperationalError):
                        await cursor.execute(
                            """INSERT INTO case_context_facts_v2
                               (fact_id,case_id,semantic_key,display_label,value_json,display_value,source_kind,status,
                                evidence_refs_json,visibility,version)
                               VALUES (%s,%s,%s,%s,%s,%s,'CUSTOMER_STATEMENT','CONFIRMED','[]','BANK_INTERNAL',1)""",
                            (f"fact-invalid-{uuid4().hex}", case_id, "transfer.actual.status", "실제 송금 여부", "{}", "송금했다고 답변"),
                        )

                    fact_id = f"fact-{uuid4().hex}"
                    await cursor.execute(
                        """INSERT INTO case_context_facts_v2
                           (fact_id,case_id,semantic_key,display_label,value_json,display_value,source_kind,status,
                            evidence_refs_json,visibility,version)
                           VALUES (%s,%s,%s,%s,%s,%s,'CUSTOMER_STATEMENT','PROPOSED','[]','BANK_INTERNAL',1)""",
                        (fact_id, case_id, "transfer.actual.status", "실제 송금 여부", "{}", "송금했다고 답변"),
                    )
                    gap_id = f"gap-{uuid4().hex}"
                    await cursor.execute(
                        """INSERT INTO case_gaps
                           (gap_id,case_id,semantic_key,title,reason,priority,status,source,evidence_refs_json,
                            related_question_ids_json,related_verification_ids_json,visibility,source_revision,version)
                           VALUES (%s,%s,%s,%s,%s,'URGENT','OPEN','AI','[]','[]','[]','BANK_INTERNAL',1,1)""",
                        (gap_id, case_id, "transfer.actual.status", "실제 송금 여부", "피해 상태 판단에 필요"),
                    )
                    with self.assertRaises(pymysql.err.IntegrityError):
                        await cursor.execute(
                            """INSERT INTO case_gaps
                               (gap_id,case_id,semantic_key,title,reason,priority,status,source,evidence_refs_json,
                                related_question_ids_json,related_verification_ids_json,visibility,source_revision,version)
                               VALUES (%s,%s,%s,%s,%s,'URGENT','OPEN','AI','[]','[]','[]','BANK_INTERNAL',1,1)""",
                            (f"gap-{uuid4().hex}", case_id, "transfer.actual.status", "중복 항목", "중복 생성 방지"),
                        )
                    await connection.commit()

                    await cursor.execute("SELECT context_revision FROM cases WHERE case_id=%s", (case_id,))
                    self.assertEqual(int((await cursor.fetchone())["context_revision"]), initial_revision + 2)
            except BaseException:
                await connection.rollback()
                raise

    async def test_case_context_v2_repository_preserves_human_decision_boundaries(self) -> None:
        case_id = f"VP-{uuid4().hex[:12]}"
        await self.repository.create(await self._record(case_id=case_id, client_request_id=uuid4().hex))
        self.case_ids.append(case_id)
        store = MySqlCaseContextV2Repository(self.repository)

        fact = await store.create_fact(case_id, {
            "client_request_id": f"fact-{uuid4().hex}",
            "semantic_key": "transfer.actual.status",
            "display_label": "실제 송금 여부",
            "value": {"status": "YES"},
            "display_value": "고객이 송금했다고 진술함",
            "evidence_refs": [{"type": "MESSAGE", "id": "msg-test"}],
        }, "operator")
        self.assertEqual(fact.status, "PROPOSED")

        gap = await store.create_gap(case_id, {
            "client_request_id": f"gap-{uuid4().hex}",
            "semantic_key": "transfer.actual.status",
            "title": "실제 송금 여부 확인",
            "reason": "피해 발생 여부 판단에 필요",
            "priority": "URGENT",
        }, "operator")
        with self.assertRaises(ContextV2TransitionError):
            await store.update_gap(case_id, gap.gap_id, 1, "RESOLVED", None, fact.fact_id, "operator")

        fact = await store.review_fact(case_id, fact.fact_id, 1, "CONFIRM", "거래 내역 확인", "owner")
        gap = await store.update_gap(case_id, gap.gap_id, 1, "RESOLVED", None, fact.fact_id, "operator")
        self.assertEqual(gap.status, "RESOLVED")

        suggestion = await store.propose_suggestion(case_id, {
            "suggestion_type": "TRANSACTION_REVIEW",
            "title": "거래 원장 확인",
            "rationale": "피해 금액 확인이 필요합니다.",
            "priority": "URGENT",
            "dedupe_key": "transaction-review:actual-transfer",
        })
        suggestion, task = await store.review_suggestion(case_id, suggestion.suggestion_id, {
            "expected_version": 1, "decision": "ACCEPT",
            "edited_title": None, "edited_description": None, "reason": None,
        }, "owner")
        self.assertEqual(suggestion.accepted_task_id, task.task_id)
        with self.assertRaises(ContextV2ConflictError):
            await store.review_suggestion(case_id, suggestion.suggestion_id, {
                "expected_version": 1, "decision": "ACCEPT",
                "edited_title": None, "edited_description": None, "reason": None,
            }, "owner")

        task = await store.complete_task(case_id, task.task_id, {
            "expected_version": 1,
            "result_summary": "거래 원장에서 송금 사실을 확인함",
            "result_code": "TRANSFER_CONFIRMED",
            "evidence_refs": [{"type": "BANK_TRANSACTION", "id": "txn-test"}],
        }, "owner")
        self.assertEqual(task.status, "COMPLETED")

        decision = await store.create_decision(case_id, {
            "client_request_id": f"decision-{uuid4().hex}",
            "decision_type": "TASK_DECISION",
            "title": "피해구제 절차 검토",
            "rationale": "송금 사실이 공식 거래 원장에서 확인됨",
            "related_entity_type": "TASK",
            "related_entity_id": task.task_id,
            "visibility": "BANK_INTERNAL",
        }, "owner")
        resources = await store.list_resources(case_id)
        self.assertEqual(resources.decisions[0].decision_id, decision.decision_id)
        self.assertEqual(resources.tasks[0].status, "COMPLETED")
        self.assertGreater(resources.context_revision, 1)

    async def _record(self, *, case_id: str, client_request_id: str) -> dict:
        source = "검찰청입니다. 지금 안전계좌로 500만원을 송금하세요."
        turns = parse_turns(source)
        extraction = EventExtraction(turns, _local_safety_events(turns), list(range(1, len(turns) + 1)), "test")
        # Repository tests must never spend API credits.
        with patch("ai_api.app.domains.diagnosis.window_ai.service.extract_events", new=AsyncMock(return_value=extraction)), patch(
            "ai_api.app.domains.diagnosis.service.extract_case_context_features",
            new=AsyncMock(return_value=CaseContextFeatures(extraction_method="LLM_INDEPENDENT")),
        ), patch(
            "ai_api.app.domains.diagnosis.service.FullContextDiagnosisHandler.analyze",
            new=AsyncMock(return_value=ContextResult(summary="테스트 사건", incident_type="test", confidence=0.8)),
        ):
            diagnosis = await DiagnosisService().analyze(source)
        diagnosis = diagnosis.model_copy(update={"case_id": case_id})
        report = InitialReportBuilder().build(case_id, diagnosis)
        now = datetime.now(timezone.utc).isoformat()
        return {
            "case_id": case_id,
            "client_request_id": client_request_id,
            "input_text": "검찰청입니다. 지금 안전계좌로 500만원을 송금하세요.",
            "risk": diagnosis.risk_level.value,
            "risk_score": diagnosis.risk_score,
            "mode": "PREVENT",
            "status": "TRIAGE",
            "initial_brief": diagnosis.context.summary,
            "diagnosis": diagnosis.model_dump(mode="json"),
            "initial_report": report.model_dump(mode="json"),
            "created_at": now,
            "updated_at": now,
        }

    async def test_context_item_transactions_and_concurrent_edits(self) -> None:
        from general_api.app.domains.cases.context_item_repository import ContextItemRepository
        from general_api.app.domains.cases.context_items import ContextItemChange, ContextItemConflictError
        case_id = f'VP-{uuid4().hex[:12]}'
        await self.repository.create(await self._record(case_id=case_id, client_request_id=uuid4().hex))
        self.case_ids.append(case_id)
        store = ContextItemRepository(self.repository)
        pool = await self.repository._get_pool()
        try:
            proposed = await asyncio.gather(*[
                store.propose(case_id, 'CLAIM', 'claim:prosecution', '검찰 소속 주장', ['event-1'])
                for _ in range(2)
            ])
            self.assertEqual(proposed[0].item_id, proposed[1].item_id)
            self.assertEqual(proposed[1].item_version, 1)
            item = proposed[0]
            outcomes = await asyncio.gather(*[
                store.change(case_id, item.item_id, ContextItemChange(expected_version=1, operation='EDIT', text=text), actor)
                for actor, text in [('staff-1', '담당자 초안 1'), ('staff-2', '담당자 초안 2')]
            ], return_exceptions=True)
            self.assertEqual(sum(isinstance(value, ContextItemConflictError) for value in outcomes), 1)
            edited = (await store.list_items(case_id))[0]
            deleted = await store.change(case_id, item.item_id, ContextItemChange(expected_version=2, operation='DELETE'), 'staff-1')
            await store.propose(case_id, 'CLAIM', 'claim:prosecution', 'AI가 다시 작성한 주장', ['event-2'])
            self.assertEqual(await store.list_items(case_id), [])
            hidden = (await store.list_items(case_id, include_deleted=True))[0]
            self.assertEqual(hidden.effective_text, edited.effective_text)
            self.assertEqual(hidden.deleted_by, deleted.deleted_by)
            with self.assertRaises(KeyError):
                await store.change('OTHER-CASE', item.item_id, ContextItemChange(expected_version=4, operation='RESTORE'), 'staff-1')
            original_save = store._save
            async def save_then_fail(*args):
                await original_save(*args)
                raise RuntimeError('simulated commit failure')
            with patch.object(store, '_save', side_effect=save_then_fail):
                with self.assertRaises(RuntimeError):
                    await store.change(case_id, item.item_id, ContextItemChange(expected_version=4, operation='RESTORE'), 'staff-1')
            self.assertEqual(await store.list_items(case_id), [])
            restored = await store.change(case_id, item.item_id, ContextItemChange(expected_version=4, operation='RESTORE'), 'staff-1')
            self.assertEqual(restored.item_version, 5)
            async with pool.acquire() as connection, connection.cursor() as cursor:
                await cursor.execute('SELECT COUNT(*) FROM case_context_item_history WHERE item_id=%s', (item.item_id,))
                self.assertEqual((await cursor.fetchone())[0], 5)
                await connection.rollback()
        finally:
            async with pool.acquire() as connection, connection.cursor() as cursor:
                await cursor.execute('DELETE FROM case_context_item_history WHERE item_id IN (SELECT item_id FROM case_context_items WHERE case_id=%s)', (case_id,))
                await cursor.execute('DELETE FROM case_context_items WHERE case_id=%s', (case_id,))
                await connection.commit()

    async def test_context_revision_and_projection_lease_are_durable(self) -> None:
        from general_api.app.domains.cases.context_projection_repository import ContextProjectionRepository

        case_id = f'VP-{uuid4().hex[:12]}'
        await self.repository.create(await self._record(case_id=case_id, client_request_id=uuid4().hex))
        self.case_ids.append(case_id)
        store = ContextProjectionRepository(self.repository)

        self.assertEqual(await store.get_revision(case_id), 1)
        claims = await asyncio.gather(store.claim(case_id, 1), store.claim(case_id, 1))
        self.assertEqual({claim.outcome for claim in claims}, {'CLAIMED', 'IN_PROGRESS'})
        owner = next(claim for claim in claims if claim.outcome == 'CLAIMED')
        self.assertFalse(await store.complete(case_id, 1, 'not-the-owner', {'value': 'wrong'}))
        self.assertTrue(await store.complete(case_id, 1, owner.lease_token, {'value': 'first'}))
        cached = await store.claim(case_id, 1)
        self.assertEqual(cached.outcome, 'CACHED')
        self.assertEqual(cached.last_success_payload, {'value': 'first'})

        await self.repository.create_personal_note(case_id, 'staff-1', '개인 메모')
        self.assertEqual(await store.get_revision(case_id), 1, '개인 메모는 사건 의미 버전을 바꾸지 않는다')
        await self.repository.create_action(case_id, {'action_type': 'PAYMENT_HOLD_REVIEW', 'actor_type': 'BANK_STAFF', 'note': '지급정지 검토'})
        self.assertEqual(await store.get_revision(case_id), 2)
        self.assertEqual((await store.claim(case_id, 1)).outcome, 'STALE')

        revision_two = await store.claim(case_id, 2)
        self.assertEqual(revision_two.outcome, 'CLAIMED')
        await self.repository.create_action(case_id, {'action_type': 'CUSTOMER_CONTACT', 'actor_type': 'BANK_STAFF', 'note': '고객 연락'})
        self.assertEqual(await store.get_revision(case_id), 3)
        self.assertFalse(await store.complete(case_id, 2, revision_two.lease_token, {'value': 'obsolete'}))
        state = await store.read(case_id)
        self.assertEqual(state['last_success_revision'], 1)
        self.assertEqual(state['last_success_payload'], {'value': 'first'})

        revision_three = await store.claim(case_id, 3)
        self.assertEqual(revision_three.outcome, 'CLAIMED')
        self.assertTrue(await store.fail(case_id, 3, revision_three.lease_token, 'AI_CONTEXT_GENERATION_FAILED'))
        failed = await store.read(case_id)
        self.assertEqual(failed['generation_status'], 'STALE')
        self.assertEqual(failed['last_success_payload'], {'value': 'first'})

    async def test_create_list_get_and_idempotency_lookup(self) -> None:
        case_id = f"A0-{uuid4().hex[:12].upper()}"
        self.case_ids.append(case_id)
        record = await self._record(case_id=case_id, client_request_id=f"a0-{uuid4().hex}")

        await self.repository.create(record)
        fetched = await self.repository.get(case_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["case_id"], case_id)
        self.assertEqual(fetched["risk"], "HIGH")
        self.assertEqual(len(fetched["initial_report"]["sections"]), 7)
        self.assertEqual((await self.repository.find_by_client_request_id(record["client_request_id"]))["case_id"], case_id)
        self.assertIn(case_id, [item["case_id"] for item in await self.repository.list()])

    async def test_trash_hides_case_then_restore_and_purge_work(self) -> None:
        case_id = f"A0-{uuid4().hex[:12].upper()}"
        self.case_ids.append(case_id)
        await self.repository.create(await self._record(case_id=case_id, client_request_id=f"trash-{uuid4().hex}"))

        await self.repository.delete_case(case_id)
        self.assertIsNone(await self.repository.get(case_id))
        self.assertNotIn(case_id, [item["case_id"] for item in await self.repository.list()])
        self.assertIn(case_id, [item["case_id"] for item in await self.repository.list_trashed_cases()])

        await self.repository.restore_case(case_id)
        self.assertIsNotNone(await self.repository.get(case_id))
        await self.repository.delete_case(case_id)
        await self.repository.purge_case(case_id)
        self.assertIsNone(await self.repository.get(case_id, include_deleted=True))

    async def test_failed_create_rolls_back_all_rows(self) -> None:
        case_id = f"A0-{uuid4().hex[:12].upper()}"
        self.case_ids.append(case_id)
        record = await self._record(case_id=case_id, client_request_id=f"a0-{uuid4().hex}")
        broken = deepcopy(record)
        broken["diagnosis"]["features"] = {"invalid_feature": "not-a-number"}

        with self.assertRaises((TypeError, ValueError)):
            await self.repository.create(broken)
        self.assertIsNone(await self.repository.get(case_id))

    async def test_message_append_and_event_cursor(self) -> None:
        case_id = f"A3-{uuid4().hex[:12].upper()}"
        self.case_ids.append(case_id)
        await self.repository.create(await self._record(case_id=case_id, client_request_id=f"a3-{uuid4().hex}"))

        request_id = f"message-{uuid4().hex}"
        message = await self.repository.append_message(case_id, {"actor_type": "CUSTOMER", "content": "송금하지 않았습니다.", "client_request_id": request_id})
        retried = await self.repository.append_message(case_id, {"actor_type": "CUSTOMER", "content": "송금하지 않았습니다.", "client_request_id": request_id})
        messages = await self.repository.list_messages(case_id)
        events = await self.repository.list_events(case_id)

        self.assertEqual(retried["message_id"], message["message_id"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["message_id"], message["message_id"])
        self.assertEqual(messages[0]["content"], "송금하지 않았습니다.")
        self.assertEqual(events[-1]["event_type"], "MESSAGE_ADDED")
        self.assertEqual(events[-1]["actor_type"], "CUSTOMER")
        self.assertEqual(await self.repository.list_events(case_id, events[-2]["event_id"]), [events[-1]])

    async def test_verification_and_action_append_events(self) -> None:
        case_id = f"A4-{uuid4().hex[:12].upper()}"
        self.case_ids.append(case_id)
        await self.repository.create(await self._record(case_id=case_id, client_request_id=f"a4-{uuid4().hex}"))

        verification = await self.repository.create_verification(case_id, {"claim": "기관 사칭", "target": "검찰청"})
        action = await self.repository.create_action(case_id, {"action_type": "HUMAN_TAKEOVER", "actor_type": "BANK_STAFF", "note": "담당자 검토 요청"})

        self.assertEqual((await self.repository.list_verifications(case_id))[0]["verification_task_id"], verification["verification_task_id"])
        self.assertEqual((await self.repository.list_actions(case_id))[0]["action_id"], action["action_id"])
        self.assertEqual([event["event_type"] for event in await self.repository.list_events(case_id)][-2:], ["VERIFICATION_CREATED", "BANK_ACTION_ADDED"])

    async def test_finalize_creates_report_card_and_reopen_restores_previous_state(self) -> None:
        case_id = f"A6-{uuid4().hex[:12].upper()}"
        self.case_ids.append(case_id)
        await self.repository.create(await self._record(case_id=case_id, client_request_id=f"a6-{uuid4().hex}"))
        sections = [
            {"section_key": "executive_summary", "content": {"text": "최종 요약"}},
            {"section_key": "resolution", "content": {"text": "사건 대응 종결"}},
        ]
        report_card = {
            "title": "최종 결과 보고서", "executive_summary": "최종 요약", "incident_summary": "기관 사칭 의심",
            "verified_facts": ["고객 진술 접수"], "actions_taken": ["송금 중단 안내"],
            "resolution": "사건 대응 종결", "follow_up": [], "cautions": [], "model_mode": "test-model",
        }

        report = await self.repository.finalize_report(case_id, 1, "종결 메모", sections, report_card)
        closed = await self.repository.get(case_id)
        messages = await self.repository.list_messages(case_id)
        reopened = await self.repository.reopen_case(case_id, 2)

        self.assertEqual(report["status"], "FINAL")
        self.assertEqual(closed["mode"], "CLOSED")
        self.assertEqual(closed["status"], "CLOSED")
        self.assertEqual(messages[-1]["message_kind"], "REPORT_CARD")
        self.assertIn("최종 결과 보고서", messages[-1]["content"])
        self.assertEqual(reopened["mode"], "PREVENT")
        self.assertEqual(reopened["status"], "TRIAGE")
        self.assertEqual(reopened["version"], 3)
        self.assertEqual([event["event_type"] for event in await self.repository.list_events(case_id)][-2:], ["CASE_REPORT_FINALIZED", "CASE_REOPENED"])

    async def test_member_upsert_is_immediately_visible_across_pool_connections(self) -> None:
        case_id = f"A5-{uuid4().hex[:12].upper()}"
        self.case_ids.append(case_id)
        await self.repository.create(await self._record(case_id=case_id, client_request_id=f"a5-{uuid4().hex}"))

        member = await self.repository.upsert_member(case_id, {
            "user_id": "bank-operator", "display_name": "은행 담당자", "role": "CHAT_OPERATOR",
        })
        members = await self.repository.list_members(case_id)

        self.assertEqual(member["user_id"], "bank-operator")
        self.assertEqual([item["user_id"] for item in members], ["bank-operator"])


    async def test_question_candidates_are_unique_across_cases_and_concurrent_writers(self) -> None:
        question = {"question_id": "q_transfer_status", "target_field": "transfer_status",
                    "question_text": "이미 송금했나요?", "reason": "피해 확인", "priority": "P0"}
        for _ in range(2):
            case_id = f"Q-{uuid4().hex[:12]}"
            self.case_ids.append(case_id)
            await self.repository.create(await self._record(case_id=case_id, client_request_id=uuid4().hex))
        first, second = self.case_ids
        batches = await asyncio.gather(
            self.repository.queue_customer_questions(first, [question], "test"),
            self.repository.queue_customer_questions(first, [question], "test"),
            self.repository.queue_customer_questions(second, [question], "test"),
        )
        ids = [row["question_id"] for batch in batches for row in batch]
        self.assertEqual(len(ids), 2)
        self.assertEqual(len(set(ids)), 2)
        self.assertNotIn("q_transfer_status", ids)
        self.assertEqual(len(await self.repository.list_customer_questions(first)), 1)
        delivered = await asyncio.gather(
            self.repository.dispatch_next_customer_question(first),
            self.repository.dispatch_next_customer_question(first),
        )
        self.assertEqual(sum(item is not None for item in delivered), 1)


class RepositorySelectionTest(unittest.TestCase):
    def test_only_mysql_repository_is_available_at_runtime(self) -> None:
        with patch.dict(os.environ, {"CASE_REPOSITORY": "memory"}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "Use mysql"):
                build_repository()
        with patch.dict(os.environ, {"CASE_REPOSITORY": "mysql"}, clear=False):
            self.assertIsInstance(build_repository(), MySqlCaseRepository)


if __name__ == "__main__":
    unittest.main()
