# Technical Brief: Local Embedding Models for Jarvis Memory Vector Search

- **Date**: 2026-04-02
- **Type**: Technical
- **Depth**: Default (7 sub-questions)
- **Sources**: 14 rated 6+/10
- **Trigger**: Gemma 4 announcement tweet + Eric asking about local model integration status

---

## Status Check: What We've Built So Far

**Nothing.** The April 1 memory consolidation research brief explicitly concluded: "No vector DB / embedding layer (overkill for ~50 file-based memories)." No embedding model, vector DB, or semantic search has been integrated.

Current memory retrieval is **grep-based** — literal string matching across ~126 markdown files in `memory/`. This works but misses semantic connections (e.g., searching "testing" won't find a signal about "defensive verification").

## What Triggered This: Gemma 4 Announcement

The [tweet](https://x.com/GoogleDeepMind/status/2039735446628925907) announces **Gemma 4** — Google DeepMind's new open model family (Apache 2.0, runs on local hardware, built for reasoning and agentic workflows). Gemma 4 is a **generative LLM**, not an embedding model.

However, Google also ships **EmbeddingGemma** (300M params, derived from Gemma 3) — a purpose-built embedding model for exactly our use case. The Gemma 4 announcement highlights Google's commitment to the local/on-device AI ecosystem that EmbeddingGemma is part of.

## The 2026 Local Embedding Landscape

### Tier 1: Best Fit for Jarvis (CPU-friendly, <500M params)

| Model | Params | Dims | Context | RAM | MTEB | License | Install |
|-------|--------|------|---------|-----|------|---------|---------|
| **EmbeddingGemma-300M** | 308M | 768 (Matryoshka) | 2048 | <200MB (QAT) | Best sub-500M | Apache 2.0 | sentence-transformers |
| **nomic-embed-text v1.5** | 137M | 768 (Matryoshka to 64) | 8192 | ~100MB | ~62 MTEB | Apache 2.0 | `ollama pull nomic-embed-text` |
| **all-MiniLM-L6-v2** | 22M | 384 | 256 | ~50MB | ~56 MTEB | Apache 2.0 | sentence-transformers |

### Tier 2: More Powerful but Heavier

| Model | Params | Dims | Context | Notes |
|-------|--------|------|---------|-------|
| **BGE-M3** | 568M | 1024 | 8192 | Hybrid dense+sparse+ColBERT. Needs GPU for good perf |
| **Qwen3-Embedding-0.6B** | 600M | 256-2048 | 8192 | Instruction-aware, flexible dims. Heavier |
| **mxbai-embed-large** | 335M | 1024 | 512 | Good English, but 512-token context is limiting |
| **Nomic Embed Text V2** | 137M (MoE) | 768 | 8192 | MoE architecture, multilingual upgrade |

### Tier 3: Cloud/API (Not Our Target)

Gemini Embedding 2, OpenAI text-embedding-3-large, Voyage-3, Cohere embed-v4 — all top performers but require API calls and send data off-device. Against our privacy-first, offline-first principles.

## Head-to-Head: EmbeddingGemma vs nomic-embed-text

These are the two real contenders for Jarvis:

| Criterion | EmbeddingGemma-300M | nomic-embed-text v1.5 |
|-----------|--------------------|-----------------------|
| **Quality (MTEB)** | Higher — best sub-500M globally | Lower (~62) but solid for English |
| **Size** | 308M params, <200MB QAT | 137M params, ~100MB |
| **Context window** | 2048 tokens | 8192 tokens |
| **Multilingual** | 100+ languages | English-focused (weak on CJK) |
| **Install friction** | pip + sentence-transformers | `ollama pull` (zero friction) |
| **Matryoshka** | Yes (768 down to smaller) | Yes (768 down to 64) |
| **Full openness** | Weights only | Weights + code + training data |
| **Ollama native** | No (not in Ollama library) | Yes |
| **Sub-15ms inference** | Yes (EdgeTPU), CPU viable | Yes (CPU native) |
| **Our doc size fit** | Good — our files are <2K tokens | Perfect — handles even large files |

**Winner for Jarvis: nomic-embed-text v1.5**

Why: (1) Ollama-native means zero-friction install on Eric's Windows machine, (2) 8K context handles any memory file without chunking, (3) smallest footprint, (4) fully auditable, (5) our corpus is English-only. EmbeddingGemma wins on raw quality but the install friction and 2K context limit tip the balance.

**Runner-up: EmbeddingGemma-300M** — upgrade path if we need higher retrieval precision later.

## Vector Storage: What Pairs With It

| Option | Type | Install | Fit for Jarvis |
|--------|------|---------|----------------|
| **ChromaDB** | Embedded DB | `pip install chromadb` | Best — zero server, Python-native, persistent |
| **LanceDB** | Embedded DB | `pip install lancedb` | Good — columnar, fast, no server |
| **numpy + cosine sim** | Raw math | Already installed | Works at <500 docs but no persistence |
| **FAISS** | Library | `pip install faiss-cpu` | Overkill — designed for millions of vectors |
| **Qdrant/Weaviate** | Server DB | Docker required | Overkill — designed for production services |

**Winner: ChromaDB** — embedded (no Docker/server), persists to disk, native Python, handles our scale perfectly.

## Do We Actually Need This?

The April 1 brief said "overkill at ~50 files." We're now at **126 files** and growing. The real question:

### When grep wins
- Exact keyword matches ("crypto-bot", "Phase 5", "steering rule")
- Known file names or paths
- Simple boolean filters

### When vector search wins
- **Semantic queries**: "what did I learn about testing reliability?" matching signals about "defensive verification" or "ISC quality gates"
- **Fuzzy recall**: finding related memories when you don't know the exact terminology
- **Cross-reference discovery**: surfacing connections between signals that use different vocabulary
- **Learning promotion**: finding synthesis-worthy signal clusters automatically

### Inflection point
At 126 files and ~284 learning signals, we're entering the zone where semantic retrieval adds real value — especially for the `/dream` consolidation skill (finding duplicates/contradictions that use different words) and synthesis (clustering related signals).

**Verdict: Yes, build it — but as a retrieval layer alongside grep, not replacing it.** Grep stays for exact lookups. Vector search adds semantic discovery.

## Recommended Architecture (Minimal Viable)

```
embedding_service.py (new utility)
├── index_memory()          # Scan memory/ + learning/, embed all .md files
├── search(query, top_k=5)  # Semantic search, return ranked file paths + snippets
├── update(file_path)       # Re-embed single file on change
└── stats()                 # Index health: file count, last indexed, stale files

Stack:
├── Model:   nomic-embed-text via Ollama (already on machine? if not: ollama pull)
├── Storage: ChromaDB (persistent, embedded, ~/.jarvis/vectorstore/)
├── Index:   One collection "jarvis_memory" with metadata (file_path, type, date)
└── Chunking: None needed — files are small enough to embed whole
```

### Integration Points
1. **`/dream` skill** — use vector similarity to find duplicate/overlapping memories
2. **Auto-memory retrieval** — session start loads relevant memories by semantic similarity to recent context
3. **Synthesis** — cluster related signals by embedding proximity instead of manual tagging
4. **`/research`** — search prior research briefs semantically before launching new research

### What NOT to Build
- No chunking pipeline (our files are small)
- No re-ranking model (overkill at this scale)
- No server/API layer (embedded DB is sufficient)
- No real-time indexing hooks (batch re-index on demand or scheduled)

## Open Questions

1. **Is Ollama already installed on Eric's machine?** If not, that's a prerequisite.
2. **Index scope**: Just `memory/` or also `learning/signals/`, `learning/synthesis/`, `history/decisions/`?
3. **Trigger for re-indexing**: Manual (`python embedding_service.py reindex`), or hook into `/learning-capture` and `/dream`?
4. **Hybrid search**: Should we implement both keyword (grep) and semantic (vector) in a single search interface, or keep them separate?

## Sources

1. [BentoML: Best Open-Source Embedding Models 2026](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models) — 9/10
2. [Google Developers: Introducing EmbeddingGemma](https://developers.googleblog.com/en/introducing-embeddinggemma/) — 9/10
3. [Milvus: Best Embedding Model for RAG 2026 (10 Models Benchmarked)](https://milvus.io/blog/choose-embedding-model-rag-2026.md) — 9/10
4. [Stark Insider: Google's EmbeddingGemma On-Device RAG](https://www.starkinsider.com/2025/09/google-embeddinggemma-on-device-rag-search.html) — 8/10
5. [PremAI: Best Embedding Models Ranked by MTEB](https://blog.premai.io/best-embedding-models-for-rag-2026-ranked-by-mteb-score-cost-and-self-hosting/) — 8/10
6. [Google AI: Generate Embeddings with Sentence Transformers](https://ai.google.dev/gemma/docs/embeddinggemma/inference-embeddinggemma-with-sentence-transformers) — 8/10
7. [Webscraft: Best Embedding Models for RAG 2026](https://webscraft.org/blog/embeddingmodeli-dlya-rag-u-2026-yak-obrati-porivnyannya-provayderiv?lang=en) — 7/10
8. [InfoQ: Google DeepMind Launches EmbeddingGemma](https://www.infoq.com/news/2025/09/embedding-gemma/) — 7/10
9. [PE Collective: Best Embedding Models 2026](https://pecollective.com/tools/best-embedding-models/) — 7/10
10. [Elephas: 13 Best Embedding Models 2026](https://elephas.app/blog/best-embedding-models) — 7/10
11. [LinkedIn: 2026 Embedding Model Landscape](https://www.linkedin.com/posts/dileeppandiya_ai-machinelearning-rag-activity-7430809962886520832-LGNw) — 7/10
12. [Ailog: MTEB Scores & Leaderboard](https://app.ailog.fr/en/blog/guides/choosing-embedding-models) — 7/10
13. [FreeCodeCamp: Run LLM Locally with Documents](https://www.freecodecamp.org/news/run-an-llm-locally-to-interact-with-your-documents/) — 6/10
14. [Latent Space: AINews Gemma 4 + Embedding Landscape](https://www.latent.space/p/ainews-autoresearch-sparks-of-recursive) — 6/10

## Recommended Next Steps

1. **Confirm Ollama status** — is it installed? `ollama --version`
2. **Quick prototype** — pull nomic-embed-text, embed 10 memory files, test 3 semantic queries, evaluate quality
3. `/architecture-review` — build-vs-buy, ChromaDB vs LanceDB vs raw numpy
4. `/create-prd` — if prototype validates, scope as a Phase 5C deliverable alongside `/dream`
