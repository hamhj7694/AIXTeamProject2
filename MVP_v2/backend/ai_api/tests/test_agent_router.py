from __future__ import annotations

import unittest

from ai_api.app.domains.case_support.agent_router import (
    BUILD_BRIEF,
    RECOMMEND_QUESTIONS,
    STRUCTURE_CUSTOMER_ANSWER,
    UPDATE_BRIEF,
    AgentRouter,
)
from ai_api.app.domains.case_support.agents import (
    CaseSupportAgent,
    CaseUpdateAgent,
    CustomerVerificationAgent,
)


class AgentRouterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.case_support = CaseSupportAgent()
        self.customer_verification = CustomerVerificationAgent()
        self.case_update = CaseUpdateAgent()
        self.router = AgentRouter(
            case_support_agent=self.case_support,
            customer_verification_agent=self.customer_verification,
            case_update_agent=self.case_update,
        )

    def test_explicit_tasks_route_to_their_owner(self) -> None:
        self.assertIs(self.router.route(BUILD_BRIEF), self.case_support)
        self.assertIs(self.router.route(RECOMMEND_QUESTIONS), self.customer_verification)
        self.assertIs(self.router.route(STRUCTURE_CUSTOMER_ANSWER), self.customer_verification)
        self.assertIs(self.router.route(UPDATE_BRIEF), self.case_update)

    def test_unknown_task_fails_explicitly(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported agent task: SEND_CUSTOMER_MESSAGE"):
            self.router.route("SEND_CUSTOMER_MESSAGE")
