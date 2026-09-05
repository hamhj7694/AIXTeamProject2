"""고객 자유응답 구조화 정책. 현재 MVP는 결정론적 규칙만 사용한다."""

ANSWER_PROMPT_VERSION = "customer-answer.v2"

ANSWER_STRUCTURING_INSTRUCTION = """\
명확한 응답만 구조화하고, 모호한 응답은 원문을 보존한 채 unresolved로 반환한다.
입력에 없는 사실을 보완하거나 추정하지 않는다.
"""
