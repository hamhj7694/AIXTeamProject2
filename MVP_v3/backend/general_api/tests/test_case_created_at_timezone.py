import unittest
from datetime import datetime

from general_api.app.domains.cases.mysql_repository import _utc_iso, _utc_naive


class CaseCreatedAtTimezoneTest(unittest.TestCase):
    def test_database_creation_time_is_normalized_to_utc(self):
        stored = _utc_naive("2026-09-05T10:15:00+09:00")
        self.assertEqual(stored, datetime(2026, 9, 5, 1, 15, 0))

    def test_database_utc_creation_time_has_offset_in_api(self):
        self.assertEqual(
            _utc_iso(datetime(2026, 9, 5, 1, 15, 0)),
            "2026-09-05T01:15:00+00:00",
        )


if __name__ == "__main__":
    unittest.main()
