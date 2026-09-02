"""Deterministic task-to-agent routing for the case-support MVP."""
from __future__ import annotations

from .agents import CaseSupportAgent, CaseUpdateAgent, CustomerVerificationAgent


BUILD_BRIEF = "BUILD_BRIEF"
RECOMMEND_QUESTIONS = "RECOMMEND_QUESTIONS"
STRUCTURE_CUSTOMER_ANSWER = "STRUCTURE_CUSTOMER_ANSWER"
UPDATE_BRIEF = "UPDATE_BRIEF"


class AgentRouter:
    """Select an owner for an explicit task without performing the task itself."""

    def __init__(
        self,
        case_support_agent: CaseSupportAgent | None = None,
        customer_verification_agent: CustomerVerificationAgent | None = None,
        case_update_agent: CaseUpdateAgent | None = None,
    ) -> None:
        case_support = case_support_agent or CaseSupportAgent()
        customer_verification = customer_verification_agent or CustomerVerificationAgent()
        case_update = case_update_agent or CaseUpdateAgent()
        self._routes = {
            BUILD_BRIEF: case_support,
            RECOMMEND_QUESTIONS: customer_verification,
            STRUCTURE_CUSTOMER_ANSWER: customer_verification,
            UPDATE_BRIEF: case_update,
        }

    def route(self, task: str) -> CaseSupportAgent | CustomerVerificationAgent | CaseUpdateAgent:
        try:
            return self._routes[task]
        except KeyError as exc:
            raise ValueError(f"Unsupported agent task: {task}") from exc
