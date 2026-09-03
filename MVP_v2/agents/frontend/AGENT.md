# Frontend Agent

## Owns

- `MVP_v2/frontend/src/**`
- React routes, API clients, Chat Shell, Case list/detail/customer/bank/verification projections

## Responsibilities

- Follow the source PRD at `MVP_v2/docs/CONTEXT_FIRST_CASE_MVP_v2_PRD_2026-09-03.md` and update `docs/new_md` when UI/data behavior changes.
- Render only API-backed Case data; never add visible fixture cases.
- Keep customer, bank, and verification views synchronized by `case_id`.
- Preserve chat drafts per Case/channel in local browser storage.
- Keep BANK_INTERNAL and AI_INTERNAL content out of customer screens.

## Before handoff

- Run `npm.cmd run build` from `MVP_v2/frontend`.
- State affected routes and manual click path.
- Request backend contract changes instead of bypassing them in the client.
