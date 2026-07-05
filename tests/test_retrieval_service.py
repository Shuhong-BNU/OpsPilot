from langchain_core.documents import Document

from app.services.retrieval_service import retrieval_service


def test_rrf_fusion_merges_dense_and_sparse_results():
    dense_docs = [
        Document(page_content="cpu 告警", metadata={"_chunk_id": "a", "_file_name": "dense.md"}),
        Document(page_content="磁盘告警", metadata={"_chunk_id": "b", "_file_name": "dense.md"}),
    ]
    sparse_docs = [
        Document(page_content="cpu 高负载处理", metadata={"_chunk_id": "a", "_file_name": "sparse.md"}),
        Document(page_content="连接池耗尽", metadata={"_chunk_id": "c", "_file_name": "sparse.md"}),
    ]

    fused = retrieval_service._rrf_fusion(dense_docs, sparse_docs)
    fused_ids = [doc.metadata["_chunk_id"] for doc in fused]

    assert fused_ids[0] == "a"
    assert "c" in fused_ids


def test_rerank_prefers_overlap_heavier_documents():
    docs = [
        Document(page_content="cpu cpu cpu usage 高负载 告警", metadata={"_chunk_id": "a"}),
        Document(page_content="磁盘空间不足", metadata={"_chunk_id": "b"}),
    ]

    reranked, _ = retrieval_service._rerank("cpu 告警", docs)

    assert reranked[0].metadata["_chunk_id"] == "a"


def test_sparse_query_builder_uses_single_token_as_is():
    assert retrieval_service._build_sparse_query("CPU") == "cpu"


def test_sparse_query_builder_uses_or_for_multiple_tokens():
    query = retrieval_service._build_sparse_query("CPU 使用率持续超过 80%")

    assert query == "\"cpu\" OR \"使用率持续超过\" OR \"80\""


def test_sparse_query_builder_handles_chinese_and_ascii_terms():
    query = retrieval_service._build_sparse_query("OOM 或频繁 GC")

    assert query == "\"oom\" OR \"或频繁\" OR \"gc\""


def test_sparse_query_builder_returns_empty_for_empty_query():
    assert retrieval_service._build_sparse_query("？！  ") == ""


def test_sparse_search_skips_empty_match_query(monkeypatch):
    called = False

    def fake_search_sparse_documents(query, top_k):
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(
        "app.services.retrieval_service.database_service.search_sparse_documents",
        fake_search_sparse_documents,
    )

    docs, _ = retrieval_service._sparse_search("？！")

    assert docs == []
    assert called is False
