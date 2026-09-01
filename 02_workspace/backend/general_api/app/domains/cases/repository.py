from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any, Protocol


class CaseRepository(Protocol):
    async def find_by_client_request_id(self, client_request_id: str) -> dict[str, Any] | None: ...
    async def get(self, case_id: str) -> dict[str, Any] | None: ...
    async def create(self, record: dict[str, Any]) -> dict[str, Any]: ...
    async def list(self) -> list[dict[str, Any]]: ...


class InMemoryCaseRepository:
    """MySQL adapter가 연결되기 전 fixture E2E용 저장소."""

    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()

    async def find_by_client_request_id(self, client_request_id: str) -> dict[str, Any] | None:
        return next((deepcopy(row) for row in self._records if row.get("client_request_id") == client_request_id), None)

    async def get(self, case_id: str) -> dict[str, Any] | None:
        return next((deepcopy(row) for row in self._records if row.get("case_id") == case_id), None)

    async def create(self, record: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            stored = deepcopy(record)
            stored.setdefault("case_id", f"VP-{len(self._records) + 1:06d}")
            self._records.append(stored)
            return deepcopy(stored)

    async def list(self) -> list[dict[str, Any]]:
        return deepcopy(self._records)
