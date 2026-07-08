"""
knowledge.py — Knowledge Schema for the AI Office RAG pipeline.

Domain models for Document, Citation, and MemoryEntry,
used across ingestion, storage, retrieval, and memory management.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Helpers ────────────────────────────────────────────────────────


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


# ── Enums ──────────────────────────────────────────────────────────


class DocumentStatus(str, Enum):
    pending = "pending"
    indexing = "indexing"
    ready = "ready"
    failed = "failed"


class ChunkStrategy(str, Enum):
    """Strategy used to split a document into chunks."""

    token = "token"  # fixed-token-size with overlap
    sentence = "sentence"  # sentence boundary split
    paragraph = "paragraph"  # blank-line-separated blocks
    header = "header"  # markdown/rST heading boundaries
    semantic = "semantic"  # embedding-similarity breakpoints


class MemoryEntryKind(str, Enum):
    fact = "fact"
    preference = "preference"
    project = "project"
    reference = "reference"
    feedback = "feedback"
    ephemeral = "ephemeral"


# ── Models ─────────────────────────────────────────────────────────


class Document(BaseModel):
    """
    A source document ingested into the knowledge base.

    The ``content`` field holds the full raw text.  Chunked
    representations live as separate ``DocumentChunk`` records
    linked by ``id``.
    """

    id: str = Field(default_factory=_new_id)
    title: str
    source: str | None = None  # file path, URL, or origin label
    content: str = ""
    content_hash: str | None = None  # sha256 of content — dedup key
    status: DocumentStatus = DocumentStatus.pending

    # Classification
    tags: list[str] = Field(default_factory=list)
    category: str | None = None  # e.g. "architecture", "research", "meeting"

    # Relationships
    parent_id: str | None = None  # for child docs (e.g. chunk-group container)
    version: int = 1

    # Embedding
    embedding_model: str | None = None  # model ID used for the document-level vector
    embedding: list[float] | None = None

    # Metadata (arbitrary)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    def touch(self) -> None:
        self.updated_at = _utcnow()

    model_config = {"frozen": False, "extra": "ignore"}


class DocumentChunk(BaseModel):
    """
    A contiguous slice of a Document, with its own embedding.

    ``content`` is the extracted text, ``offset`` is the character
    position within the parent document (0-based), and ``length``
    is the number of characters in this chunk.
    """

    id: str = Field(default_factory=_new_id)
    document_id: str
    index: int = 0  # ordinal within the document (0-based)
    content: str
    offset: int = 0
    length: int = 0

    strategy: ChunkStrategy = ChunkStrategy.token
    strategy_params: dict[str, Any] = Field(default_factory=dict)

    embedding_model: str | None = None
    embedding: list[float] | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=_utcnow)

    model_config = {"frozen": False, "extra": "ignore"}


class Citation(BaseModel):
    """
    A verifiable reference to a specific location inside a source document.

    ``text`` should capture the *exact* quoted span so readers can
    verify the claim without opening the source.
    """

    id: str = Field(default_factory=_new_id)
    document_id: str
    chunk_id: str | None = None  # points to the DocumentChunk that contains this text

    text: str  # exact quoted span
    source_location: str | None = None  # page / line numbers / section heading

    # Context
    context_before: str | None = None  # ~50 chars preceding the quote
    context_after: str | None = None  # ~50 chars following the quote

    # Confidence
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    verified: bool = False

    # Relationships (polymorphic)
    target_type: str | None = None  # e.g. "memory", "document", "report"
    target_id: str | None = None  # ID of the thing this citation supports

    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)

    model_config = {"frozen": False, "extra": "ignore"}


class MemoryEntry(BaseModel):
    """
    A persistent piece of information the office should remember
    across conversations.

    Roughly analogous to a row in the ``memory/`` directory, but
    optimised for programmatic retrieval via the RAG pipeline.
    """

    id: str = Field(default_factory=_new_id)
    name: str  # short kebab-case slug
    description: str = ""
    content: str  # the fact / knowledge body

    kind: MemoryEntryKind = MemoryEntryKind.fact
    tags: list[str] = Field(default_factory=list)

    # Embedding
    embedding_model: str | None = None
    embedding: list[float] | None = None

    # Links to related memories ([[slug]] references resolved to IDs)
    related_memory_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)

    # Importance / expiry
    priority: int = Field(default=0, ge=0, le=10)  # 0 = normal, 10 = pinned
    expires_at: datetime | None = None
    access_count: int = 0
    last_accessed_at: datetime | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    def touch(self) -> None:
        self.updated_at = _utcnow()

    model_config = {"frozen": False, "extra": "ignore"}


# ── Search / Query models ─────────────────────────────────────────


class SearchQuery(BaseModel):
    """Structured query for the RAG retrieval pipeline."""

    text: str
    top_k: int = Field(default=5, ge=1, le=100)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)

    # Filters
    tags: list[str] | None = None
    categories: list[str] | None = None
    kinds: list[MemoryEntryKind] | None = None

    # Hybrid search weight (0 = pure keyword, 1 = pure semantic)
    semantic_weight: float = Field(default=0.7, ge=0.0, le=1.0)


class SearchResult(BaseModel):
    """A single hit from the retrieval pipeline."""

    id: str
    content: str
    score: float
    source: str | None = None
    rank: int = 0

    # Full entity — populated when the caller requests full hydration
    entity: Document | DocumentChunk | MemoryEntry | None = None


# ── Pipeline models ───────────────────────────────────────────────


class IngestionResult(BaseModel):
    """Outcome of ingesting a document into the knowledge base."""

    document_id: str
    chunks_created: int = 0
    citations_extracted: int = 0
    status: DocumentStatus


class RetrievalContext(BaseModel):
    """
    Packaged context block fed to the generator (LLM) in a RAG pipeline.

    ``text`` is the flattened, deduplicated context window.
    ``citations`` are attached so the generator can produce
    verifiable inline references.
    """

    query: str
    text: str
    chunks: list[DocumentChunk] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    memories: list[MemoryEntry] = Field(default_factory=list)
    total_tokens_estimated: int = 0
