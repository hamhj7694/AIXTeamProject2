from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class OfficialSourceMatch:
    source_id: str
    title: str
    excerpt: str
    source_uri: str


class OfficialVerificationSource(Protocol):
    """Boundary for a curated official corpus; a search hit never completes verification."""

    async def search(self, query: str) -> list[OfficialSourceMatch]: ...


class UnavailableOfficialVerificationSource:
    """MVP provider until an approved corpus and deployment credentials exist."""

    async def search(self, query: str) -> list[OfficialSourceMatch]:
        del query
        return []


# TODO: add an approved provider only with a curated official corpus,
# provenance policy, evaluation fixtures, and deployment credentials.
official_verification_source: OfficialVerificationSource = UnavailableOfficialVerificationSource()
