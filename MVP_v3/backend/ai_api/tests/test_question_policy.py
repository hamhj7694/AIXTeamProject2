from __future__ import annotations

import unittest

from ai_api.app.domains.case_support.question_policy import QuestionSource, normalize_question


def question(**updates):
    value = {
        "question_id": "q-1",
        "target_field": "exposure_scope",
        "question_text": "어떤 정보를 제공하셨나요?",
        "reason": "노출 범위를 확인해야 합니다.",
        "priority": "P1",
        "options": ["계좌번호", "신분증", "OTP"],
        "answer_mode": "CHOICE_OR_TEXT",
        "allow_free_text": True,
    }
    value.update(updates)
    return value


class QuestionPolicyTest(unittest.TestCase):
    def test_default_is_single_select(self) -> None:
        result = normalize_question(question(), source=QuestionSource.LLM)

        self.assertFalse(result.allow_multi_select)
        self.assertEqual(result.source, QuestionSource.LLM)

    def test_explicit_multi_select_is_preserved(self) -> None:
        result = normalize_question(
            question(allow_multi_select=True), source=QuestionSource.LLM,
        )

        self.assertTrue(result.allow_multi_select)
        self.assertEqual(len(result.options), 3)

    def test_options_are_trimmed_deduplicated_and_blank_values_are_removed(self) -> None:
        result = normalize_question(
            question(options=[" 계좌번호 ", "", "계좌번호", "신분증"]), source=QuestionSource.LLM,
        )

        self.assertEqual(result.options, ["계좌번호", "신분증"])

    def test_invalid_multi_select_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            normalize_question(
                question(options=["계좌번호", "계좌번호"], allow_multi_select=True),
                source=QuestionSource.LLM,
            )

    def test_more_than_eight_unique_options_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            normalize_question(
                question(options=[f"선택 {index}" for index in range(9)]), source=QuestionSource.LLM,
            )

    def test_malformed_options_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            normalize_question(question(options="계좌번호"), source=QuestionSource.LLM)
        with self.assertRaises(ValueError):
            normalize_question(question(options=["계좌번호", 123]), source=QuestionSource.LLM)

    def test_malformed_multi_select_flag_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            normalize_question(question(allow_multi_select="true"), source=QuestionSource.LLM)

    def test_text_question_does_not_keep_options_or_multi_select(self) -> None:
        result = normalize_question(
            question(answer_mode="TEXT", allow_multi_select=True), source=QuestionSource.LLM,
        )

        self.assertEqual(result.options, [])
        self.assertFalse(result.allow_multi_select)
        self.assertTrue(result.allow_free_text)

    def test_source_distinguishes_deterministic_and_llm_questions(self) -> None:
        deterministic = normalize_question(question(), source=QuestionSource.DETERMINISTIC)
        llm = normalize_question(question(), source=QuestionSource.LLM)

        self.assertEqual(deterministic.source, QuestionSource.DETERMINISTIC)
        self.assertEqual(llm.source, QuestionSource.LLM)

    def test_sensitive_value_request_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            normalize_question(
                question(question_text="OTP 인증번호를 입력해 주세요."), source=QuestionSource.LLM,
            )


if __name__ == "__main__":
    unittest.main()
