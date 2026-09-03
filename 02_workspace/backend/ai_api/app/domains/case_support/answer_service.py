"""고객의 단일 자유응답을 계약에 맞는 안전한 구조로 변환한다."""
from __future__ import annotations

import re

from contracts.ai_internal.mvp_workflow import CustomerAnswerResult, TargetField

from .answer_prompt import ANSWER_PROMPT_VERSION

_REQUEST_ONLY_MARKERS = (
    "\ud558\ub77c\uace0", "\uc694\uccad", "\uc694\uad6c", "\uad8c\uc720", "\uc2dc\ud0a4", "\ud574\uc57c", "\ud558\ub77c",
)


_AMBIGUOUS_MARKERS = ("모르", "같", "아마", "듯", "수도", "추측", "기억안", "기억이안")


class CustomerAnswerStructuringService:
    """명확한 긍정·부정만 결정론적으로 처리하며, 나머지는 안전하게 보류한다."""

    prompt_version = ANSWER_PROMPT_VERSION

    def structure_answer(self, target_field: TargetField, raw_answer: str) -> CustomerAnswerResult:
        text = raw_answer.strip()
        normalized = self._normalize(text)
        value = self._structure_known_field(target_field, normalized)

        if value is None:
            return CustomerAnswerResult(
                target_field=target_field,
                raw_answer=text,
                structured_value=None,
                confidence=0.0,
                unresolved=True,
                evidence_text=text,
                warnings=["답변이 불명확하거나 현재 MVP 지원 범위를 벗어나 담당자 확인이 필요합니다."],
            )

        return CustomerAnswerResult(
            target_field=target_field,
            raw_answer=text,
            structured_value=value,
            confidence=0.95,
            unresolved=False,
            evidence_text=text,
            warnings=[],
        )

    def _structure_known_field(self, target_field: TargetField, text: str) -> str | None:
        if not text or any(marker in text for marker in _AMBIGUOUS_MARKERS):
            return None
        if target_field is TargetField.TRANSFER_STATUS:
            return self._yes_no_value(
                text,
                negative=("송금안", "송금하지않", "송금한적없", "이체안", "이체하지않", "안보냈", "보내지않", "입금안"),
                positive=("송금했", "송금완료", "이체했", "이체완료", "보냈", "입금했"),
                no_value="NOT_TRANSFERRED",
                yes_value="TRANSFERRED",
            )
        if target_field is TargetField.PERSONAL_INFORMATION_EXPOSURE:
            return self._yes_no_value(
                text,
                negative=("제공안", "제공하지않", "안알려", "알려주지않", "입력안", "유출안"),
                positive=("제공했", "알려줬", "알려주었", "입력했", "유출됐", "유출되었"),
                no_value="NOT_EXPOSED",
                yes_value="EXPOSED",
            )
        if target_field is TargetField.AUTHENTICATION_INFORMATION_EXPOSURE:
            return self._yes_no_value(
                text,
                negative=("제공안", "제공하지않", "안알려", "알려주지않", "입력안"),
                positive=("제공했", "알려줬", "알려주었", "입력했"),
                no_value="NOT_EXPOSED",
                yes_value="EXPOSED",
            )
        return None

    @staticmethod
    def _yes_no_value(
        text: str,
        *,
        negative: tuple[str, ...],
        positive: tuple[str, ...],
        no_value: str,
        yes_value: str,
    ) -> str | None:
        if any(pattern in text for pattern in negative):
            return no_value
        # A request to provide information is not proof it was actually provided.
        # Explicit negative answers above remain usable when a request is mentioned.
        if any(marker in text for marker in _REQUEST_ONLY_MARKERS):
            return None
        if any(pattern in text for pattern in positive):
            return yes_value
        return None

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"[\s.,!?~]", "", text).lower()
