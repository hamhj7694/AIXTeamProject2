from __future__ import annotations

import unittest

from contracts.public_api.case_context_v2 import PublicCaseContextResourcesV2
from general_api.app.domains.cases.context_v3.panel import build_context_panel_v3


class ContextPopulationContractTests(unittest.TestCase):
    def test_customer_projection_does_not_leak_empty_bank_resources(self):
        panel = build_context_panel_v3(
            {"case_id": "VP-1", "context_revision": 2},
            PublicCaseContextResourcesV2(case_id="VP-1", context_revision=2),
            view="customer", verifications=[], actions=[], messages=[], progress=[],
        )
        self.assertEqual(panel.source_revision, 2)
        self.assertEqual([item.item_id for section in panel.sections for item in section.items], [])

