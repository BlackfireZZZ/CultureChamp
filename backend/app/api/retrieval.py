"""Shared retrieval dependency for direct context search and chat generation."""

from functools import lru_cache
from typing import cast

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.retrieval import RetrievalService
from app.core.config import settings
from app.infrastructure.db.hybrid_search import SqlGovernedHybridSearch
from app.infrastructure.db.session import session_factory
from app.infrastructure.vector.local_retrieval import LocalCrossEncoderReranker, RussianBM25
from app.infrastructure.vector.text_vectors import LocalTextEmbedder, QdrantTextIndex


@lru_cache(maxsize=1)
def _components() -> tuple[QdrantTextIndex, LocalCrossEncoderReranker, RussianBM25]:
    return (QdrantTextIndex(settings.vector_url, LocalTextEmbedder()),
            LocalCrossEncoderReranker(settings.retrieval_model_cache, settings.retrieval_device),
            RussianBM25())


def get_retrieval_service(request: Request) -> RetrievalService:
    factory = cast(async_sessionmaker[AsyncSession], getattr(
        request.app.state, "source_session_factory", session_factory))
    index, reranker, lexical = _components()
    return RetrievalService(SqlGovernedHybridSearch(
        factory,
        getattr(request.app.state, "vector_index", index),
        getattr(request.app.state, "retrieval_reranker", reranker),
        getattr(request.app.state, "retrieval_lexical", lexical),
    ))
