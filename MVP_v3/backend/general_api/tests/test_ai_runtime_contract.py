from __future__ import annotations

import unittest

from general_api.app.clients.diagnosis_ai import AiServiceAuthenticationError, AiServiceTimeoutError
from contracts.public_api.ai_runtime import runtime_error


class AiRuntimeContractTests(unittest.TestCase):
    def test_provider_timeout_is_retryable_and_has_stable_code(self):
        error = AiServiceTimeoutError("timeout")
        self.assertEqual(error.code, "AI_PROVIDER_TIMEOUT")
        self.assertTrue(error.retryable)

    def test_auth_error_is_not_retryable(self):
        error = AiServiceAuthenticationError("auth")
        self.assertEqual(error.code, "AI_PROVIDER_AUTH_ERROR")
        self.assertFalse(error.retryable)

    def test_public_error_keeps_legacy_code_additively(self):
        payload = runtime_error("AI_PROVIDER_UNAVAILABLE", "retry", retryable=True, legacy_code="OLD")
        self.assertEqual(payload["code"], "AI_PROVIDER_UNAVAILABLE")
        self.assertEqual(payload["legacy_code"], "OLD")
        self.assertTrue(payload["retryable"])

