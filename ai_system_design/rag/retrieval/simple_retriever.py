"""mvp_chunks.json을 직접 검색하는 의존성 없는 문자 n-gram Retriever."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


RAG_DIRECTORY = Path(__file__).resolve().parents[1]
DEFAULT_CHUNKS_PATH = RAG_DIRECTORY / "chunks" / "mvp_chunks.json"
NGRAM_SIZES = (2, 3, 4)
# 현재 MVP Corpus에서 확인된 신고/제보 표현 차이만 Query 단계에서 보완한다.
QUERY_SYNONYMS = {"신고": ("제보",), "제보": ("신고",)}


class SimpleRetriever:
    """작은 한국어 Corpus를 위한 character n-gram TF-IDF cosine Retriever."""

    def __init__(self, chunks_path: Path | None = None) -> None:
        self.chunks_path = chunks_path or DEFAULT_CHUNKS_PATH
        self.chunks = self._load_chunks(self.chunks_path)
        self._document_terms = [self._terms(self._searchable_text(chunk)) for chunk in self.chunks]
        self._idf = self._build_idf(self._document_terms)
        self._document_vectors = [self._tfidf_vector(terms) for terms in self._document_terms]

    def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """질문과 유사한 Chunk만 score 내림차순으로 반환한다."""
        if top_k < 1:
            raise ValueError("top_k must be at least 1")

        query_vector = self._tfidf_vector(self._terms(self._expand_query(query)))
        if not query_vector:
            return []

        ranked_results: list[tuple[float, dict[str, Any]]] = []
        for chunk, document_vector in zip(self.chunks, self._document_vectors):
            score = self._cosine_similarity(query_vector, document_vector)
            # 겹치는 문자 n-gram이 없는 Chunk는 관련 결과처럼 반환하지 않는다.
            if score > 0:
                ranked_results.append((score, self._result_item(chunk, score)))

        ranked_results.sort(key=lambda item: item[0], reverse=True)
        return [
            {"rank": rank, **result}
            for rank, (_, result) in enumerate(ranked_results[:top_k], start=1)
        ]

    @staticmethod
    def _load_chunks(chunks_path: Path) -> list[dict[str, Any]]:
        with chunks_path.open("r", encoding="utf-8") as source_file:
            chunks = json.load(source_file)
        if not isinstance(chunks, list):
            raise ValueError("mvp_chunks.json must contain a JSON list")
        return chunks

    @staticmethod
    def _searchable_text(chunk: dict[str, Any]) -> str:
        # Source ID와 URL은 출처 추적용이므로 검색 본문에 포함하지 않는다.
        values = [
            chunk.get("title", ""),
            chunk.get("text", ""),
            chunk.get("knowledge_purpose", ""),
            chunk.get("applicable_context", ""),
        ]
        return " ".join(str(value) for value in values if value)

    @staticmethod
    def _terms(text: str) -> Counter[str]:
        normalized = re.sub(r"\s+", " ", text.strip().lower())
        if len(normalized) < min(NGRAM_SIZES):
            return Counter()
        return Counter(
            normalized[index : index + size]
            for size in NGRAM_SIZES
            for index in range(len(normalized) - size + 1)
        )

    @staticmethod
    def _expand_query(query: str) -> str:
        """MVP Corpus와 대표 질문 사이에서 확인된 소수 표현만 보완한다."""
        synonyms = [
            synonym
            for term, alternatives in QUERY_SYNONYMS.items()
            if term in query
            for synonym in alternatives
        ]
        return " ".join([query, *synonyms])

    def _build_idf(self, document_terms: list[Counter[str]]) -> dict[str, float]:
        document_count = len(document_terms)
        document_frequency = Counter(
            term for terms in document_terms for term in terms.keys()
        )
        return {
            term: math.log((1 + document_count) / (1 + frequency)) + 1
            for term, frequency in document_frequency.items()
        }

    def _tfidf_vector(self, terms: Counter[str]) -> dict[str, float]:
        if not terms:
            return {}
        term_total = sum(terms.values())
        return {
            term: (count / term_total) * self._idf[term]
            for term, count in terms.items()
            if term in self._idf
        }

    @staticmethod
    def _cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
        dot_product = sum(value * right.get(term, 0.0) for term, value in left.items())
        if dot_product == 0:
            return 0.0
        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))
        return dot_product / (left_norm * right_norm)

    @staticmethod
    def _result_item(chunk: dict[str, Any], score: float) -> dict[str, Any]:
        return {
            "score": round(score, 6),
            "knowledge_id": chunk["knowledge_id"],
            "title": chunk["title"],
            "knowledge_purpose": chunk["knowledge_purpose"],
            "source_id": chunk["source_id"],
            "source_agency": chunk["source_agency"],
            "source_url": chunk["source_url"],
            "covers_questions": chunk["covers_questions"],
            "text": chunk["text"],
        }
