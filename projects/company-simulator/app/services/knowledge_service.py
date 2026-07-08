"""
knowledge_service.py — RAG pipeline for the AI Office knowledge core.

Provides ingestion, chunking, embedding, vector storage (abstract),
semantic / hybrid search, citation extraction, and memory management.
"""

from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.models.knowledge import (
    ChunkStrategy,
    Citation,
    Document,
    DocumentChunk,
    DocumentStatus,
    IngestionResult,
    MemoryEntry,
    MemoryEntryKind,
    RetrievalContext,
    SearchQuery,
)


# ── Embedding provider (abstract) ─────────────────────────────────


class EmbeddingProvider(ABC):
    """Pluggable embedding interface.  Swap in OpenAI/Qdrant/ LiteLLM etc."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return a list of dense vectors, one per input text."""
        ...

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Return a single query vector (may use a different model/prefix)."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier stored alongside embeddings for lineage."""
        ...


# ── Vector store (abstract) ───────────────────────────────────────


class VectorStore(ABC):
    """Abstract vector index.  Implementations: Qdrant, PGVector, FAISS, etc."""

    @abstractmethod
    async def upsert(self, collection: str, vectors: list[tuple[str, list[float], dict]]) -> None:
        """Upsert (id, vector, payload) tuples into *collection*."""
        ...

    @abstractmethod
    async def search(
        self,
        collection: str,
        vector: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[str, float, dict]]:
        """Return (id, score, payload) nearest neighbours."""
        ...

    @abstractmethod
    async def delete(self, collection: str, ids: list[str]) -> None:
        """Delete vectors by ID."""
        ...

    @abstractmethod
    async def delete_collection(self, collection: str) -> None:
        """Drop an entire collection."""
        ...


# ── Chunking strategies ───────────────────────────────────────────


@dataclass
class ChunkResult:
    """Output of a single chunking pass."""

    chunks: list[DocumentChunk]
    strategy: ChunkStrategy
    params: dict[str, Any]


def chunk_by_token(
    text: str,
    document_id: str,
    *,
    max_tokens: int = 512,
    overlap_tokens: int = 64,
    approx_chars_per_token: int = 4,
) -> ChunkResult:
    """Split *text* into fixed-size token windows with overlap.

    Uses a simple character-count proxy for token length.  Swap in
    a real tokeniser (tiktoken, etc.) when exact counts are needed.
    """
    chunk_size = max_tokens * approx_chars_per_token
    stride = chunk_size - overlap_tokens * approx_chars_per_token
    if stride <= 0:
        stride = chunk_size // 2

    chunks: list[DocumentChunk] = []
    start = 0
    index = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        content = text[start:end]
        chunks.append(
            DocumentChunk(
                document_id=document_id,
                index=index,
                content=content,
                offset=start,
                length=end - start,
                strategy=ChunkStrategy.token,
                strategy_params={"max_tokens": max_tokens, "overlap_tokens": overlap_tokens},
            )
        )
        index += 1
        if end >= len(text):
            break
        start += stride

    return ChunkResult(
        chunks, ChunkStrategy.token, {"max_tokens": max_tokens, "overlap_tokens": overlap_tokens}
    )


def chunk_by_sentence(
    text: str,
    document_id: str,
    *,
    max_sentences: int = 8,
    overlap_sentences: int = 1,
) -> ChunkResult:
    """Split on sentence boundaries (``. ! ?`` followed by whitespace/end)."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks: list[DocumentChunk] = []
    stride = max_sentences - overlap_sentences
    if stride <= 0:
        stride = 1

    for i in range(0, len(sentences), stride):
        group = sentences[i : i + max_sentences]
        content = " ".join(group)
        # approximate offset by concatenating prior sentences
        prior = " ".join(sentences[:i])
        offset = len(prior) + (1 if prior else 0)
        chunks.append(
            DocumentChunk(
                document_id=document_id,
                index=len(chunks),
                content=content,
                offset=offset,
                length=len(content),
                strategy=ChunkStrategy.sentence,
                strategy_params={
                    "max_sentences": max_sentences,
                    "overlap_sentences": overlap_sentences,
                },
            )
        )

    return ChunkResult(
        chunks,
        ChunkStrategy.sentence,
        {"max_sentences": max_sentences, "overlap_sentences": overlap_sentences},
    )


def chunk_by_paragraph(
    text: str,
    document_id: str,
    *,
    max_paragraphs: int = 4,
) -> ChunkResult:
    """Split on blank-line boundaries (common in markdown/rST)."""
    paragraphs = re.split(r"\n\s*\n", text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks: list[DocumentChunk] = []
    for i in range(0, len(paragraphs), max_paragraphs):
        group = paragraphs[i : i + max_paragraphs]
        content = "\n\n".join(group)
        prior = "\n\n".join(paragraphs[:i])
        offset = len(prior) + (2 if prior else 0)
        chunks.append(
            DocumentChunk(
                document_id=document_id,
                index=len(chunks),
                content=content,
                offset=offset,
                length=len(content),
                strategy=ChunkStrategy.paragraph,
                strategy_params={"max_paragraphs": max_paragraphs},
            )
        )

    return ChunkResult(chunks, ChunkStrategy.paragraph, {"max_paragraphs": max_paragraphs})


def chunk_by_header(
    text: str,
    document_id: str,
) -> ChunkResult:
    """Split on markdown headings (``# `` / ``## `` etc.)."""
    # Split on heading lines, keeping the heading as part of the chunk
    parts = re.split(r"(^#{1,6}\s+.*$)", text, flags=re.MULTILINE)
    # Re-pair: heading + body
    chunks: list[DocumentChunk] = []
    offset = 0
    idx = 0
    i = 0
    while i < len(parts):
        heading = parts[i]
        i += 1
        body = parts[i] if i < len(parts) and not parts[i].startswith("#") else ""
        if body:
            i += 1
        content = heading + body
        chunks.append(
            DocumentChunk(
                document_id=document_id,
                index=idx,
                content=content.strip(),
                offset=offset,
                length=len(content),
                strategy=ChunkStrategy.header,
                strategy_params={},
            )
        )
        offset += len(content)
        idx += 1

    return ChunkResult(chunks, ChunkStrategy.header, {})


# ── Text utilities ────────────────────────────────────────────────

CHUNKERS: dict[ChunkStrategy, Callable[..., ChunkResult]] = {
    ChunkStrategy.token: chunk_by_token,
    ChunkStrategy.sentence: chunk_by_sentence,
    ChunkStrategy.paragraph: chunk_by_paragraph,
    ChunkStrategy.header: chunk_by_header,
}


def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_citations(text: str, document_id: str) -> list[Citation]:
    """Heuristic citation extractor.

    Looks for patterns like:
      - Quoted spans ("...")
      - Markdown links ``[text](url)``
      - Bracketed references ``[1]``, ``[2]`` etc.
    """
    citations: list[Citation] = []

    # Quoted spans
    for match in re.finditer(r'"([^"]{20,})"', text):
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)
        citations.append(
            Citation(
                document_id=document_id,
                text=match.group(1),
                context_before=text[start : match.start()].strip() or None,
                context_after=text[match.end() : end].strip() or None,
            )
        )

    # Markdown reference-style links
    for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", text):
        citations.append(
            Citation(
                document_id=document_id,
                text=match.group(1),
                source_location=match.group(2),
            )
        )

    # Inline bracketed references
    for match in re.finditer(r"\[(\d+(?:[,;\s]+\d+)*)\]", text):
        citations.append(
            Citation(
                document_id=document_id,
                text=text[max(0, match.start() - 80) : match.end() + 20].strip(),
                source_location=f"ref {match.group(1)}",
            )
        )

    return citations


# ── Service ────────────────────────────────────────────────────────


class KnowledgeService:
    """Main RAG pipeline — ingestion, retrieval, memory management.

    Usage::

        svc = KnowledgeService(embedder=my_embedder, store=my_vector_store)
        result = await svc.ingest_document(doc)
        ctx = await svc.retrieve("What is the architecture?")
    """

    def __init__(
        self,
        embedder: EmbeddingProvider,
        vector_store: VectorStore,
        *,
        default_chunk_strategy: ChunkStrategy = ChunkStrategy.token,
        default_top_k: int = 5,
    ) -> None:
        self._embedder = embedder
        self._store = vector_store
        self._default_strategy = default_chunk_strategy
        self._default_top_k = default_top_k

        # In-memory stores (swap for Postgres / Redis when scaling)
        self._documents: dict[str, Document] = {}
        self._chunks: dict[str, DocumentChunk] = {}
        self._citations: dict[str, Citation] = {}
        self._memories: dict[str, MemoryEntry] = {}

    # ── Documents ──────────────────────────────────────────────────

    async def ingest_document(
        self,
        doc: Document,
        *,
        strategy: ChunkStrategy | None = None,
        strategy_params: dict[str, Any] | None = None,
        reindex: bool = False,
    ) -> IngestionResult:
        """Ingest a document: hash-dedup → chunk → embed → index.

        Returns IDs and counts for the ingested artefacts.
        """
        # Dedup by content hash
        doc.content_hash = compute_hash(doc.content)
        existing = [d for d in self._documents.values() if d.content_hash == doc.content_hash]
        if existing and not reindex:
            return IngestionResult(
                document_id=existing[0].id,
                chunks_created=0,
                citations_extracted=0,
                status=DocumentStatus.ready,
            )

        doc.status = DocumentStatus.indexing
        self._documents[doc.id] = doc

        # 1. Chunk
        chunker = CHUNKERS.get(strategy or self._default_strategy, chunk_by_token)
        params = strategy_params or {}
        chunk_result = chunker(doc.content, doc.id, **params)

        chunks = chunk_result.chunks
        doc.touch()

        # 2. Embed chunks in batches
        texts = [c.content for c in chunks]
        embeddings = await self._embedder.embed(texts)
        for c, vec in zip(chunks, embeddings):
            c.embedding = vec
            c.embedding_model = self._embedder.model_name
            self._chunks[c.id] = c

        # 3. Index in vector store
        vectors = [
            (c.id, c.embedding, {"document_id": c.document_id, "index": c.index})
            for c in chunks
            if c.embedding is not None
        ]
        if vectors:
            await self._store.upsert("documents", vectors)

        # 4. Extract citations
        citations = extract_citations(doc.content, doc.id)
        for cit in citations:
            # Link to the chunk that contains the citation text
            for c in chunks:
                if cit.text in c.content:
                    cit.chunk_id = c.id
                    break
            self._citations[cit.id] = cit

        doc.status = DocumentStatus.ready
        doc.touch()

        return IngestionResult(
            document_id=doc.id,
            chunks_created=len(chunks),
            citations_extracted=len(citations),
            status=DocumentStatus.ready,
        )

    async def get_document(self, doc_id: str) -> Document | None:
        return self._documents.get(doc_id)

    async def delete_document(self, doc_id: str) -> None:
        self._documents.pop(doc_id, None)
        chunk_ids = [cid for cid, c in self._chunks.items() if c.document_id == doc_id]
        for cid in chunk_ids:
            self._chunks.pop(cid, None)
        if chunk_ids:
            await self._store.delete("documents", chunk_ids)

    def list_documents(self) -> list[Document]:
        return list(self._documents.values())

    # ── Retrieval ──────────────────────────────────────────────────

    async def retrieve(
        self,
        query: str | SearchQuery,
        *,
        top_k: int | None = None,
        min_score: float = 0.0,
        hydrate: bool = False,
    ) -> RetrievalContext:
        """End-to-end RAG retrieval.

        1. Embed the query
        2. Vector search over chunk store
        3. Look up matching MemoryEntries
        4. Collect citations
        5. Package into a ``RetrievalContext``
        """
        if isinstance(query, str):
            q = SearchQuery(text=query, top_k=top_k or self._default_top_k, min_score=min_score)
        else:
            q = query

        qvec = await self._embedder.embed_query(q.text)

        # Vector search
        hits = await self._store.search(
            "documents",
            qvec,
            top_k=q.top_k,
            filters=self._build_filters(q),
        )

        chunks: list[DocumentChunk] = []
        scores: dict[str, float] = {}
        for chunk_id, score, _ in hits:
            if score < q.min_score:
                continue
            chunk = self._chunks.get(chunk_id)
            if chunk is None:
                continue
            chunks.append(chunk)
            scores[chunk.id] = score

        # Deduplicate and sort by score desc
        seen: set[str] = set()
        unique: list[DocumentChunk] = []
        for c in sorted(chunks, key=lambda x: scores.get(x.id, 0), reverse=True):
            if c.id not in seen:
                seen.add(c.id)
                unique.append(c)

        # Related memories (semantic search over memory entries)
        memory_hits = await self._search_memories(qvec, top_k=q.top_k)
        memories = [m for m, _ in memory_hits]

        # Collect citations for retrieved chunk documents
        doc_ids = {c.document_id for c in unique}
        citations = [cit for cit in self._citations.values() if cit.document_id in doc_ids]

        # Assemble context text
        context_parts = []
        for c in unique:
            header = f"[Chunk {c.index}]"
            context_parts.append(f"{header}\n{c.content}")
        context_text = "\n\n".join(context_parts)

        # Rough token estimate (very approximate)
        total_est = len(context_text) // 4 + sum(len(m.content) // 4 for m in memories)

        return RetrievalContext(
            query=q.text,
            text=context_text,
            chunks=unique[: q.top_k],
            citations=citations,
            memories=memories,
            total_tokens_estimated=total_est,
        )

    def _build_filters(self, q: SearchQuery) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        if q.tags:
            filters["tags"] = q.tags
        if q.categories:
            filters["categories"] = q.categories
        return filters

    # ── Memory entries ─────────────────────────────────────────────

    async def create_memory(
        self,
        entry: MemoryEntry,
        *,
        embed: bool = True,
    ) -> MemoryEntry:
        """Store a new memory entry and optionally embed it."""
        self._memories[entry.id] = entry

        if embed and entry.content:
            vecs = await self._embedder.embed([entry.content])
            entry.embedding = vecs[0]
            entry.embedding_model = self._embedder.model_name
            await self._store.upsert(
                "memories",
                [
                    (
                        entry.id,
                        entry.embedding,
                        {
                            "name": entry.name,
                            "kind": entry.kind.value,
                            "tags": entry.tags,
                            "priority": entry.priority,
                        },
                    ),
                ],
            )

        return entry

    async def get_memory(self, memory_id: str) -> MemoryEntry | None:
        return self._memories.get(memory_id)

    async def update_memory(self, memory_id: str, **updates: Any) -> MemoryEntry | None:
        entry = self._memories.get(memory_id)
        if entry is None:
            return None
        for field, val in updates.items():
            if hasattr(entry, field):
                setattr(entry, field, val)
        entry.touch()

        # Re-embed if content changed
        if "content" in updates:
            vecs = await self._embedder.embed([entry.content])
            entry.embedding = vecs[0]
            entry.embedding_model = self._embedder.model_name
            await self._store.upsert(
                "memories",
                [
                    (entry.id, entry.embedding, {"name": entry.name, "kind": entry.kind.value}),
                ],
            )

        return entry

    async def delete_memory(self, memory_id: str) -> None:
        self._memories.pop(memory_id, None)
        await self._store.delete("memories", [memory_id])

    def list_memories(self, kind: MemoryEntryKind | None = None) -> list[MemoryEntry]:
        if kind is None:
            return list(self._memories.values())
        return [m for m in self._memories.values() if m.kind == kind]

    async def _search_memories(
        self,
        query_vector: list[float],
        top_k: int = 5,
    ) -> list[tuple[MemoryEntry, float]]:
        hits = await self._store.search("memories", query_vector, top_k=top_k)
        results: list[tuple[MemoryEntry, float]] = []
        for mem_id, score, _ in hits:
            mem = self._memories.get(mem_id)
            if mem is not None:
                results.append((mem, score))
        return results

    # ── Citations ──────────────────────────────────────────────────

    def add_citation(self, citation: Citation) -> Citation:
        self._citations[citation.id] = citation
        return citation

    def get_citations_for_document(self, doc_id: str) -> list[Citation]:
        return [c for c in self._citations.values() if c.document_id == doc_id]

    def get_citations_for_target(self, target_type: str, target_id: str) -> list[Citation]:
        return [
            c
            for c in self._citations.values()
            if c.target_type == target_type and c.target_id == target_id
        ]

    # ── Admin / introspection ──────────────────────────────────────

    async def reindex_all(self) -> int:
        """Re-embed all documents.  Returns count of documents reindexed."""
        count = 0
        for doc in self._documents.values():
            await self.ingest_document(doc, reindex=True)
            count += 1
        return count

    async def health(self) -> dict[str, Any]:
        return {
            "documents": len(self._documents),
            "chunks": len(self._chunks),
            "citations": len(self._citations),
            "memories": len(self._memories),
            "embedder": self._embedder.model_name,
        }

    def clear(self) -> None:
        """Reset all in-memory stores (for testing)."""
        self._documents.clear()
        self._chunks.clear()
        self._citations.clear()
        self._memories.clear()
