"""RagKnowledgeService의 독립 실행 가능한 최소 검증."""

from __future__ import annotations

import unittest

try:
    from .rag_service import RagKnowledgeService
except ImportError:  # python ai_system_design/rag/service/test_rag_service.py 실행 지원
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from ai_system_design.rag.service.rag_service import RagKnowledgeService


class RagKnowledgeServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = RagKnowledgeService()

    def test_general_search_returns_source_traceability(self) -> None:
        response = self.service.search("검찰에서 안전계좌로 돈을 보내라고 할 수 있나?")

        self.assertTrue(response["has_results"])
        result = response["results"][0]
        self.assertTrue(result["source_id"])
        self.assertTrue(result["source_url"])

    def test_recovery_search_includes_recovery_knowledge(self) -> None:
        response = self.service.search("이미 송금했는데 피해구제 절차를 확인하고 싶어")

        knowledge_ids = {result["knowledge_id"] for result in response["results"]}
        self.assertIn("REC-001", knowledge_ids)

    def test_security_search_includes_kisa_knowledge(self) -> None:
        response = self.service.search("원격제어 앱을 설치하라고 했는데 어떻게 확인해야 해?")

        self.assertTrue(
            any(result["source_id"] == "SRC-002" for result in response["results"])
        )

    def test_blank_query_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.service.search("   ")

    def test_top_k_limits_result_count(self) -> None:
        response = self.service.search("피싱 신고 절차를 알려줘", top_k=1)

        self.assertLessEqual(len(response["results"]), 1)

    def test_no_retrieval_results_is_not_an_error(self) -> None:
        class EmptyRetriever:
            def search(self, query: str, top_k: int = 3) -> list[dict[str, object]]:
                return []

        response = RagKnowledgeService(retriever=EmptyRetriever()).search("관련 없는 질문")

        self.assertFalse(response["has_results"])
        self.assertEqual(response["results"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
