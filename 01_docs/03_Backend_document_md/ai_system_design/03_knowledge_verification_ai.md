# Knowledge & Verification AI 설계

> 현재 상태: DESIGN_ONLY. Corpus·Source Registry·Embedding·Vector Index·RAG 실행 코드는 아직 없으며 향후 책임은 B=lee다.

## 1. 역할

공식문서 검색과 주장 비교를 담당한다. 외부 검증 Token, 기관 연락, 응답 저장은 일반 Backend가 처리하며 이 서비스는 실제 외부 연락을 실행하지 않는다.

## 2. 내부 구성

```text
Knowledge Registry(MySQL)
  ↓ 활성·최신 Source 필터
Vector Retriever
  ↓
Reranker
  ↓
근거 기반 비교·요약
```

Retriever/Embedding/Reranker는 Tool/Pipeline이며 자율 Agent가 아니다.

## 3. 기능

| 기능 | 결과 |
|---|---|
| Verification | 주장과 공식절차의 일치/불일치/확인 필요 |
| Response Guide | 현재 필요한 안전행동 근거 |
| Recovery Guide | 피해구제·신고·후속조치 근거 |
| Institution Info | 기관 역할·정상 업무절차 근거 |

## 4. API 연결

```text
POST /ai/rag/search
POST /ai/rag/verify-claim
POST /ai/rag/response-guide
POST /ai/rag/recovery-guide
POST /ai/rag/institution-info
```

## 5. 응답 필수 Metadata

```json
{
  "assessment": "MATCH | MISMATCH | NEEDS_VERIFICATION",
  "sources": [{
    "source_id": "src_...",
    "chunk_id": "chunk_...",
    "agency": "...",
    "title": "...",
    "source_url": "...",
    "effective_date": "...",
    "evidence": "...",
    "retrieval_score": 0.0
  }]
}
```

## 6. 일반 코드 경계

- `official_contacts`의 전화번호·URL은 Backend가 MySQL에서 조회한다.
- Source 수집 상태와 최신성은 `knowledge_sources`에서 관리한다.
- 실제 사용 근거는 Backend가 `case_evidence`에 저장한다.
- Verification Task 상태와 외부 Token은 Backend가 관리한다.

## 7. 평가

- 검색 Recall@K·MRR 또는 합의된 Retrieval 지표
- 공식 Source 인용 정확도
- 오래되거나 비활성 Source 노출 여부
- 답변 Claim과 인용 근거의 정합성
- 검색 결과 없음 시 환각 차단
- 평균·P95 Latency와 Embedding/LLM 비용

## 8. 완료조건

- [ ] Source Registry·Chunk Metadata Schema 확정
- [ ] Chunk/Embedding/Index Pipeline 구축
- [ ] 최신성 필터·Reranking 구현
- [ ] 네 가지 RAG 응답 Contract Test
- [ ] `case_evidence` 저장 통합 테스트
- [ ] 공식 연락처 생성 금지 테스트
