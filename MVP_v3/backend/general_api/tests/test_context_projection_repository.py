import unittest
from unittest.mock import AsyncMock

from general_api.app.domains.cases.context_projection_repository import ContextProjectionRepository


class ContextProjectionValidationTest(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_claim_is_rejected_before_database_access(self):
        cases = AsyncMock()
        store = ContextProjectionRepository(cases)
        for revision, lease in [(0, 45), (1, 4), (1, 301)]:
            with self.assertRaises(ValueError):
                await store.claim('VP-1', revision, lease_seconds=lease)
        cases._get_pool.assert_not_awaited()

    def test_json_payload_parser_accepts_driver_shapes(self):
        self.assertEqual(ContextProjectionRepository._json({'a': 1}), {'a': 1})
        self.assertEqual(ContextProjectionRepository._json('{"a": 1}'), {'a': 1})
        self.assertEqual(ContextProjectionRepository._json(b'{"a": 1}'), {'a': 1})
        self.assertIsNone(ContextProjectionRepository._json(None))
