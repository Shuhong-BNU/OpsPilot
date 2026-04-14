"""混合检索与轻量重排服务."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document
from loguru import logger

from app.config import config
from app.services.database_service import database_service
from app.services.metrics_service import metrics_service
from app.services.session_service import utc_now
from app.services.vector_store_manager import vector_store_manager


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_\u4e00-\u9fff]+")


@dataclass
class RetrievalTrace:
    query: str
    dense_hits: int
    sparse_hits: int
    fusion_hits: int
    rerank_hits: int
    dense_latency_ms: int
    sparse_latency_ms: int
    rerank_latency_ms: int
    final_sources: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "dense_hits": self.dense_hits,
            "sparse_hits": self.sparse_hits,
            "fusion_hits": self.fusion_hits,
            "rerank_hits": self.rerank_hits,
            "dense_latency_ms": self.dense_latency_ms,
            "sparse_latency_ms": self.sparse_latency_ms,
            "rerank_latency_ms": self.rerank_latency_ms,
            "final_sources": self.final_sources,
        }


class RetrievalService:
    """提供 dense recall + sparse recall + RRF + rerank."""

    def hybrid_search(self, query: str) -> tuple[list[Document], RetrievalTrace]:
        dense_docs, dense_latency_ms = self._dense_search(query)
        sparse_docs, sparse_latency_ms = self._sparse_search(query)
        fused = self._rrf_fusion(dense_docs, sparse_docs)
        reranked, rerank_latency_ms = self._rerank(query, fused)

        trace = RetrievalTrace(
            query=query,
            dense_hits=len(dense_docs),
            sparse_hits=len(sparse_docs),
            fusion_hits=len(fused),
            rerank_hits=len(reranked),
            dense_latency_ms=dense_latency_ms,
            sparse_latency_ms=sparse_latency_ms,
            rerank_latency_ms=rerank_latency_ms,
            final_sources=[
                doc.metadata.get("_file_name", "unknown")
                for doc in reranked
            ],
        )

        metrics_service.observe("rag_dense_search_latency", dense_latency_ms)
        metrics_service.observe("rag_sparse_search_latency", sparse_latency_ms)
        metrics_service.observe("rag_rerank_latency", rerank_latency_ms)
        metrics_service.observe(
            "rag_retrieval_latency",
            dense_latency_ms + sparse_latency_ms + rerank_latency_ms,
        )
        return reranked, trace

    def persist_chunks(self, source_path: str, documents: list[Document]) -> None:
        """将切片写入 SQLite，供稀疏检索使用."""
        database_service.delete_document_chunks_by_source(source_path)
        chunk_rows: list[dict[str, Any]] = []
        for document in documents:
            metadata = dict(document.metadata)
            chunk_rows.append(
                {
                    "chunk_id": metadata.get("_chunk_id", str(uuid.uuid4())),
                    "source_path": source_path,
                    "file_name": metadata.get("_file_name", source_path.split("/")[-1]),
                    "content": document.page_content,
                    "metadata": metadata,
                    "content_hash": hashlib.sha256(document.page_content.encode("utf-8")).hexdigest(),
                    "created_at": utc_now(),
                }
            )
        database_service.upsert_document_chunks(chunk_rows)

    def _dense_search(self, query: str) -> tuple[list[Document], int]:
        from time import perf_counter

        start = perf_counter()
        docs = vector_store_manager.similarity_search(query, k=config.dense_top_k)
        elapsed = int((perf_counter() - start) * 1000)
        return docs, elapsed

    def _sparse_search(self, query: str) -> tuple[list[Document], int]:
        from time import perf_counter

        start = perf_counter()
        sparse_query = " ".join(TOKEN_PATTERN.findall(query.lower())) or query
        rows = database_service.search_sparse_documents(sparse_query, config.sparse_top_k)
        docs = [
            Document(
                page_content=row["content"],
                metadata={
                    "_chunk_id": row["chunk_id"],
                    "_source": row["source_path"],
                    "_file_name": row["file_name"],
                    "_sparse_score": row["score"],
                },
            )
            for row in rows
        ]
        elapsed = int((perf_counter() - start) * 1000)
        return docs, elapsed

    def _rrf_fusion(self, dense_docs: list[Document], sparse_docs: list[Document]) -> list[Document]:
        scores: dict[str, float] = {}
        docs_by_key: dict[str, Document] = {}

        def key_for(document: Document) -> str:
            return document.metadata.get("_chunk_id") or hashlib.sha1(
                document.page_content.encode("utf-8")
            ).hexdigest()

        for index, document in enumerate(dense_docs, start=1):
            key = key_for(document)
            docs_by_key[key] = document
            scores[key] = scores.get(key, 0.0) + 1.0 / (60 + index)

        for index, document in enumerate(sparse_docs, start=1):
            key = key_for(document)
            docs_by_key[key] = document
            scores[key] = scores.get(key, 0.0) + 1.0 / (60 + index)

        ranked_keys = sorted(scores, key=scores.get, reverse=True)[: config.hybrid_top_k]
        return [docs_by_key[key] for key in ranked_keys]

    def _rerank(self, query: str, docs: list[Document]) -> tuple[list[Document], int]:
        from time import perf_counter

        start = perf_counter()
        query_tokens = set(TOKEN_PATTERN.findall(query.lower()))

        def doc_score(document: Document) -> float:
            content_tokens = set(TOKEN_PATTERN.findall(document.page_content.lower()))
            overlap = len(query_tokens & content_tokens)
            length_penalty = max(len(document.page_content) / 800.0, 1.0)
            return overlap / length_penalty

        reranked = sorted(docs, key=doc_score, reverse=True)[: config.rerank_top_k]
        elapsed = int((perf_counter() - start) * 1000)
        return reranked, elapsed

    @staticmethod
    def format_docs(docs: list[Document]) -> str:
        """格式化检索文档为上下文."""
        parts = []
        for index, doc in enumerate(docs, start=1):
            metadata = doc.metadata
            headers = [metadata.get("h1"), metadata.get("h2"), metadata.get("h3")]
            title = " > ".join([header for header in headers if header])
            source = metadata.get("_file_name", "未知来源")
            item = [f"【参考资料 {index}】", f"来源: {source}"]
            if title:
                item.append(f"标题: {title}")
            item.append(f"内容:\n{doc.page_content}")
            parts.append("\n".join(item))
        return "\n\n".join(parts)

    @staticmethod
    def summarize_trace(trace: RetrievalTrace) -> str:
        """序列化 trace，便于落库和调试."""
        return json.dumps(trace.to_dict(), ensure_ascii=False)


retrieval_service = RetrievalService()
