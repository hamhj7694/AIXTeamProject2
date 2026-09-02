# Backend Agent

## Owns

- `MVP_v2/backend/general_api/**`
- `MVP_v2/backend/contracts/public_api/**`
- `MVP_v2/backend/migrations/**`

## Responsibilities

- Maintain Case as the shared source of truth for messages, participants, verification, reports, and event logs.
- Keep local SQLite behavior compatible with the repository protocol and MySQL path.
- Add events only for meaningful Case milestones, not every UI interaction.
- Enforce audience/channel separation at API boundaries.

## Before handoff

- Run `python -m unittest discover -s general_api/tests -v` from `MVP_v2/backend`.
- Document API request/response changes in the appropriate public contract.
