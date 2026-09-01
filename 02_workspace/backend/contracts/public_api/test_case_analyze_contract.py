from __future__ import annotations

import json
import unittest
from pathlib import Path

from pydantic import ValidationError

from contracts.public_api.case_analyze import (
    PublicAnalyzeCaseRequest,
    PublicAnalyzeCaseResponse,
)


class PublicAnalyzeContractTest(unittest.TestCase):
    def setUp(self) -> None:
        example_path = Path(__file__).with_name("case_analyze.v1.example.json")
        self.example = json.loads(example_path.read_text(encoding="utf-8"))

    def test_examples_match_public_contract(self) -> None:
        PublicAnalyzeCaseRequest.model_validate(self.example["request"])
        for response in self.example["responses"].values():
            PublicAnalyzeCaseResponse.model_validate(response)

    def test_request_rejects_empty_text_but_preserves_optional_empty_id_behavior(self) -> None:
        with self.assertRaises(ValidationError):
            PublicAnalyzeCaseRequest.model_validate({"text": ""})
        request = PublicAnalyzeCaseRequest.model_validate({"text": "정상 상담", "client_request_id": ""})
        self.assertEqual(request.client_request_id, "")

    def test_public_response_rejects_ai_internal_fields(self) -> None:
        payload = dict(self.example["responses"]["CASE_CREATED"])
        payload["diagnosis"] = {"model_metadata": {"model_name": "internal-only"}}
        with self.assertRaises(ValidationError):
            PublicAnalyzeCaseResponse.model_validate(payload)

    def test_failed_response_does_not_accept_internal_error_details(self) -> None:
        payload = dict(self.example["responses"]["FAILED"])
        payload["error"] = {**payload["error"], "details": {"cause": "internal-only"}}
        with self.assertRaises(ValidationError):
            PublicAnalyzeCaseResponse.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
