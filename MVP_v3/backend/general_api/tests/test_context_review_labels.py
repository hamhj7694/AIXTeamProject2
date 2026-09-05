import unittest

from general_api.app.domains.cases.repository import normalize_target_field
from general_api.app.domains.cases.signal_projection import _label
from types import SimpleNamespace


class ContextLabelsTest(unittest.TestCase):
    def test_legacy_field_aliases_have_one_identity(self):
        for value in ['PERSONAL_INFO', 'personal_info_shared', 'personal_information_exposure']:
            self.assertEqual(normalize_target_field(value), 'personal_information_exposure')
        self.assertEqual(normalize_target_field('AUTH_INFO_SHARED'), 'authentication_information_exposure')

    def test_unknown_subtype_does_not_expose_english_family(self):
        for family in ['IMPERSONATION', 'ACTION_REQUEST', 'PSY_STRATEGY', 'MONEY_MOVEMENT', 'AMOUNT']:
            label = _label(SimpleNamespace(event_family=family, subtype='NEW_SUBTYPE'))
            self.assertNotIn(family, label)
            self.assertNotIn('신호', label)

    def test_known_specific_signal_is_retained(self):
        self.assertEqual(_label(SimpleNamespace(event_family='IMPERSONATION', subtype='PROSECUTION')), '검찰·수사기관 사칭')
