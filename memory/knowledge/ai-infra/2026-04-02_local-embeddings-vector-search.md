---
domain: ai-infra
source: /research (backfill)
date: 2026-04-02
topic: Local Embedding Models for Jarvis Memory Vector Search
confidence: 8
source_files:
  - memory/work/local-embeddings/research_brief.md
tags: [embeddings, vector-search, nomic-embed, chromadb, local-models, memory, semantic-search]
---

## Key Findings
- Current memory retrieval is grep-based (literal string matching across ~126 markdown files) — works but misses semantic connections; embedding layer is not yet built
- **Winner: nomic-embed-text v1.5** (137M params, 768-dim Matryoshka, 8192-token context, ~100MB RAM) — Ollama-native (`ollama pull nomic-embed-text`), handles any memory file without chunking, fully auditable, English-focused; installs in seconds on Windows
- **Runner-up: EmbeddingGemma-300M** (Google DeepMind, Apache 2.0) — higher raw MTEB quality and multilingual, but not in Ollama library (requires pip + sentence-transformers) and 2048-token context limit is constraining for larger files
- **Vector storage winner: ChromaDB** — embedded (no Docker/server), persists to disk, Python-native (`pip install chromadb`), handles Jarvis's scale perfectly; FAISS and Qdrant/Weaviate are overkill (designed for millions of vectors / production services)
- Cloud embedding APIs (Gemini Embedding 2, OpenAI text-embedding-3-large, Voyage-3, Cohere) top the quality rankings but send data off-device — against Jarvis's privacy-first, offline-first principles

## Context
Triggered by the Gemma 4 announcement (Google DeepMind, Apache 2.0, reasoning + agentic workflows). Gemma 4 is a generative LLM, not an embedding model; the relevant sibling is EmbeddingGemma-300M. The April 1 memory consolidation brief previously concluded "no vector DB needed (overkill for ~50 files)" — the corpus has since grown to ~126 files, making semantic search increasingly valuable. nomic-embed-text's Ollama-native installation is the decisive advantage for Windows + zero-friction setup.

## Open Questions
- At what corpus size (files or total tokens) does the semantic search quality improvement justify the ChromaDB overhead?
- Should the embedding index be rebuilt nightly or incrementally on file change?
- What is the right chunking strategy for long markdown files with mixed content (headers, code blocks, tables)?
