from __future__ import annotations

import unittest

from general_api.app.domains.cases.repository import InMemoryCaseRepository


class AiGenerationSupersedeRepositoryTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.repository = InMemoryCaseRepository()
        await self.repository.create({
            "case_id": "CASE-SUPERSEDE",
            "initial_report": {"report_id": "report-1"},
            "created_at": "2026-09-20T00:00:00+00:00",
        })

    async def append_human(self, content: str, *, actor_type: str, actor_user_id: str, channel: str) -> dict:
        message = await self.repository.append_message("CASE-SUPERSEDE", {
            "actor_type": actor_type,
            "actor_user_id": actor_user_id,
            "actor_display_name": actor_user_id,
            "actor_role": actor_type,
            "content": content,
            "channel": channel,
            "audience": "CUSTOMER" if channel == "CUSTOMER" else "BANK_INTERNAL",
            "visibility": "CUSTOMER" if channel == "CUSTOMER" else "BANK_INTERNAL",
            "message_kind": "CHAT",
            "client_request_id": f"request-{actor_user_id}-{content}",
        })
        assert message is not None
        return message

    async def test_new_same_stream_message_blocks_obsolete_ai_response(self) -> None:
        first = await self.append_human("A", actor_type="BANK_STAFF", actor_user_id="staff-1", channel="TEAM")
        second = await self.append_human("B", actor_type="BANK_STAFF", actor_user_id="staff-1", channel="TEAM")

        stale = await self.repository.append_message("CASE-SUPERSEDE", {
            "actor_type": "BANK_AGENT", "actor_user_id": "case-copilot", "content": "A only",
            "channel": "TEAM", "audience": "BANK_INTERNAL", "visibility": "BANK_INTERNAL",
            "message_kind": "AI_RESPONSE", "client_request_id": "ai-stale",
        }, source_guard={
            "source_message_ids": [first["message_id"]], "channel": "TEAM",
            "actor_type": "BANK_STAFF", "actor_user_id": "staff-1",
        })
        self.assertIsNone(stale)
        self.assertFalse(any(item.get("client_request_id") == "ai-stale" for item in await self.repository.list_messages("CASE-SUPERSEDE")))

        current = await self.repository.append_message("CASE-SUPERSEDE", {
            "actor_type": "BANK_AGENT", "actor_user_id": "case-copilot", "content": "A and B",
            "channel": "TEAM", "audience": "BANK_INTERNAL", "visibility": "BANK_INTERNAL",
            "message_kind": "AI_RESPONSE", "client_request_id": "ai-current",
        }, source_guard={
            "source_message_ids": [first["message_id"], second["message_id"]], "channel": "TEAM",
            "actor_type": "BANK_STAFF", "actor_user_id": "staff-1",
        })
        self.assertIsNotNone(current)

    async def test_other_requester_and_channel_do_not_supersede_source_stream(self) -> None:
        source = await self.append_human("customer A", actor_type="CUSTOMER", actor_user_id="customer-1", channel="CUSTOMER")
        await self.append_human("other customer", actor_type="CUSTOMER", actor_user_id="customer-2", channel="CUSTOMER")
        await self.append_human("bank message", actor_type="BANK_STAFF", actor_user_id="staff-1", channel="TEAM")

        current = await self.repository.append_message("CASE-SUPERSEDE", {
            "actor_type": "CUSTOMER_AGENT", "actor_user_id": "customer-agent", "content": "reply",
            "channel": "CUSTOMER", "audience": "CUSTOMER", "visibility": "CUSTOMER",
            "message_kind": "AI_RESPONSE", "client_request_id": "customer-ai-current",
        }, source_guard={
            "source_message_ids": [source["message_id"]], "channel": "CUSTOMER",
            "actor_type": "CUSTOMER", "actor_user_id": "customer-1",
        })
        self.assertIsNotNone(current)


if __name__ == "__main__":
    unittest.main()
