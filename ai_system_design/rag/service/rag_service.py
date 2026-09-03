"""SimpleRetriever를 호출자 친화적인 반환 형식으로 감싼 Service."""

from __future__ import annotations

from typing import Any

from ..retrieval.simple_retriever import SimpleRetriever


class RagKnowledgeService:
    """공식 Knowledge를 검색할 뿐 Case 상태나 조치를 판단하지 않는다."""

    def __init__(self, retriever: SimpleRetriever | None = None) -> None:
        self._retriever = retriever or SimpleRetriever()

    def search(self, query: str, top_k: int = 3) -> dict[str, Any]:
        """업무 Query에 대한 공식 Knowledge Top-K와 출처 정보를 반환한다."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        if top_k < 1:
            raise ValueError("top_k must be at least 1")

        results = self._retriever.search(query, top_k=top_k)
        return {
            "query": query,
            "top_k": top_k,
            "has_results": bool(results),
            "results": results,
        }
