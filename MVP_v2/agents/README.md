# MVP_v2 AI Agent Team

This folder is the operating guide for the MVP_v2 delivery team. Each agent owns a bounded area; no agent edits another owner's area without an explicit handoff from the Orchestrator.

## Team

| Agent | Primary responsibility | Main files |
|---|---|---|
| Orchestrator | scope, dependency order, integration, release checks | `agents/orchestrator/` |
| Frontend | React routes, Case views, Chat UI, client state | `frontend/src/**` |
| Backend | General API, SQLite/MySQL repositories, public contracts | `backend/general_api/**`, `backend/contracts/public_api/**` |
| AI | diagnosis, agent invocation, RAG and AI-internal contracts | `backend/ai_api/**`, `backend/contracts/ai_internal/**` |
| UI/UX | interaction specifications, accessibility, visual QA | `agents/uiux/` and UI review only |
| Product | requirements, acceptance criteria, priority decisions | `agents/product/` |
| User Liaison | communicate decisions, demos, questions, and feedback | `agents/user_liaison/` |

## Shared operating rules

1. `Case` data in the backend repository is the single source of truth. Browser mocks cannot become a data source.
2. Public API changes require backend ownership and frontend review; AI-internal changes require AI ownership and backend review.
3. The Orchestrator assigns file ownership before implementation when work crosses a boundary.
4. Every completed change includes its verification command or manual acceptance path.
5. Never expose BANK_INTERNAL or AI_INTERNAL data in the customer projection.

Read the relevant role document before beginning work.
