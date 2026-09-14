from __future__ import annotations

import unittest

from general_api.app.domains.cases.context_v3.official_verification import (
    OfficialSourceMatch,
    UnavailableOfficialVerificationSource,
)


class OfficialVerificationSourceBoundaryTest(unittest.IsolatedAsyncioTestCase):
    async def test_unconfigured_official_source_returns_no_invented_results(self) -> None:
        self.assertEqual(await UnavailableOfficialVerificationSource().search("검찰청 계좌"), [])

    async def test_fixture_provider_can_implement_the_boundary_without_completing_a_task(self) -> None:
        class FixtureSource:
            async def search(self, query: str) -> list[OfficialSourceMatch]:
                return [OfficialSourceMatch("official-1", query, "fixture excerpt", "fixture://official-1")]

        result = await FixtureSource().search("공식 기관 확인")
        self.assertEqual(result[0].source_id, "official-1")
        self.assertFalse(hasattr(result[0], "verification_status"))


if __name__ == "__main__":
    unittest.main()
