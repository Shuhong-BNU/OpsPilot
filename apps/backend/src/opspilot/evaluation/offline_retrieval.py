"""Offline deterministic adapter around the production retrieval tool.

Only external dependencies are replaced. Candidate fusion, scope filtering,
BM25L, RRF, result shaping, and stage-rank evidence use KnowledgeRetrievalTool.
"""

from __future__ import annotations

import asyncio
import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from opspilot.llm import RerankResult
from opspilot.retrieval import KnowledgeRetrievalTool, KnowledgeRetrievalToolInput
from opspilot.retrieval.hybrid import tokenize_hybrid_text
from opspilot.vector_store import StoredVectorChunk, VectorSearchResult

EVALUATION_OWNER_ID = "eval-user"
EVALUATION_KNOWLEDGE_BASE_ID = "eval-kb"
_VECTOR_DIMENSIONS = 256


@dataclass(frozen=True, slots=True)
class OfflineEvaluationCase:
    """One retrieval-only case with source-level ground truth."""

    id: str
    question: str
    relevant_sources: tuple[str, ...]
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OfflineEvaluationResult:
    """Scored result and stage evidence for one offline retrieval case."""

    case: OfflineEvaluationCase
    sources: tuple[str, ...]
    first_relevant_rank: int | None
    hit_at_1: int
    hit_at_3: int
    reciprocal_rank: float
    recall_at_3: float
    stage_evidence: tuple[Mapping[str, object], ...]


def load_markdown_corpus(corpus_dir: Path) -> list[StoredVectorChunk]:
    """Load one deterministic evaluation chunk per Markdown document."""
    chunks: list[StoredVectorChunk] = []
    for path in sorted(corpus_dir.glob("*.md")):
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            continue
        chunks.append(
            StoredVectorChunk(
                chunk_id=f"eval-{path.stem}",
                document_id=path.name,
                knowledge_base_id=EVALUATION_KNOWLEDGE_BASE_ID,
                owner_user_id=EVALUATION_OWNER_ID,
                tenant_id=EVALUATION_OWNER_ID,
                content=content,
                source=path.name,
                created_at=0,
                metadata={"knowledgeType": "sop", "evaluationMode": "offline-v2"},
            )
        )
    if not chunks:
        raise ValueError(f"No Markdown documents found in {corpus_dir}")
    return chunks


def build_offline_retrieval_tool(chunks: Sequence[StoredVectorChunk]) -> KnowledgeRetrievalTool:
    """Build the real retrieval tool with deterministic local adapters."""
    return KnowledgeRetrievalTool(
        embedding_model=_DeterministicEmbeddingModel(),
        vector_store=_InMemoryEvaluationVectorStore(chunks),
        rerank_model=_DeterministicRerankModel(),
    )


def evaluate_offline_cases(
    tool: KnowledgeRetrievalTool, cases: Sequence[OfflineEvaluationCase]
) -> list[OfflineEvaluationResult]:
    """Run cases synchronously for scripts and CI without external services."""
    return [asyncio.run(_evaluate_case(tool, case)) for case in cases]


async def _evaluate_case(
    tool: KnowledgeRetrievalTool, case: OfflineEvaluationCase
) -> OfflineEvaluationResult:
    retrieval = await tool.run(
        KnowledgeRetrievalToolInput(query=case.question, top_k=3),
        owner_user_id=EVALUATION_OWNER_ID,
        accessible_knowledge_base_ids=(EVALUATION_KNOWLEDGE_BASE_ID,),
    )
    sources = tuple(hit.source for hit in retrieval.results)
    relevant = set(case.relevant_sources)
    first_rank = next(
        (index for index, source in enumerate(sources, start=1) if source in relevant),
        None,
    )
    retrieved_relevant = sum(source in relevant for source in sources[:3])
    evidence = tuple(
        {
            "source": hit.source,
            "chunk_id": hit.chunk_id,
            "vector_rank": hit.vector_rank,
            "bm25_rank": hit.bm25_rank,
            "rerank_rank": hit.rerank_rank,
            "vector_score": hit.vector_score,
            "bm25_score": hit.bm25_score,
            "rrf_score": hit.rrf_score,
            "rerank_score": hit.rerank_score,
        }
        for hit in retrieval.results
    )
    return OfflineEvaluationResult(
        case=case,
        sources=sources,
        first_relevant_rank=first_rank,
        hit_at_1=int(first_rank == 1),
        hit_at_3=int(first_rank is not None and first_rank <= 3),
        reciprocal_rank=0.0 if first_rank is None else 1 / first_rank,
        recall_at_3=retrieved_relevant / len(relevant),
        stage_evidence=evidence,
    )


class _DeterministicEmbeddingModel:
    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return [_token_hash_vector(text) for text in texts]


class _InMemoryEvaluationVectorStore:
    def __init__(self, chunks: Sequence[StoredVectorChunk]) -> None:
        self._chunks = list(chunks)
        self._vectors = {chunk.chunk_id: _token_hash_vector(chunk.content) for chunk in chunks}

    def search_chunks(
        self,
        *,
        query_vector: Sequence[float],
        tenant_id: str,
        knowledge_base_ids: Sequence[str],
        limit: int,
    ) -> list[VectorSearchResult]:
        scored = [
            (chunk, _cosine_similarity(query_vector, self._vectors[chunk.chunk_id]))
            for chunk in self._scoped_chunks(tenant_id, knowledge_base_ids)
        ]
        scored.sort(key=lambda item: (-item[1], item[0].source))
        return [
            VectorSearchResult(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                knowledge_base_id=chunk.knowledge_base_id,
                owner_user_id=chunk.owner_user_id,
                tenant_id=chunk.tenant_id,
                content=chunk.content,
                source=chunk.source,
                created_at=chunk.created_at,
                metadata=chunk.metadata,
                score=score,
            )
            for chunk, score in scored[:limit]
        ]

    def list_chunks(
        self, *, tenant_id: str, knowledge_base_ids: Sequence[str]
    ) -> list[StoredVectorChunk]:
        return self._scoped_chunks(tenant_id, knowledge_base_ids)

    def _scoped_chunks(
        self, tenant_id: str, knowledge_base_ids: Sequence[str]
    ) -> list[StoredVectorChunk]:
        allowed = set(knowledge_base_ids)
        return [
            chunk
            for chunk in self._chunks
            if chunk.tenant_id == tenant_id and chunk.knowledge_base_id in allowed
        ]


class _DeterministicRerankModel:
    async def arerank(
        self, *, query: str, documents: Sequence[str], top_n: int
    ) -> list[RerankResult]:
        query_tokens = set(tokenize_hybrid_text(query))
        scored = [
            (index, _overlap_score(query_tokens, set(tokenize_hybrid_text(document))))
            for index, document in enumerate(documents)
        ]
        scored.sort(key=lambda item: (-item[1], item[0]))
        return [
            RerankResult(index=index, relevance_score=score)
            for index, score in scored[:top_n]
        ]


def _token_hash_vector(text: str) -> list[float]:
    vector = [0.0] * _VECTOR_DIMENSIONS
    for token in tokenize_hybrid_text(text):
        bucket = int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:4], "big")
        vector[bucket % _VECTOR_DIMENSIONS] += 1.0
    return vector


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    denominator = math.sqrt(sum(a * a for a in left) * sum(b * b for b in right))
    return numerator / denominator if denominator else 0.0


def _overlap_score(query_tokens: set[str], document_tokens: set[str]) -> float:
    if not query_tokens or not document_tokens:
        return 0.0
    return len(query_tokens & document_tokens) / len(query_tokens)
