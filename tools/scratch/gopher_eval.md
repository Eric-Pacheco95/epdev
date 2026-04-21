# TheCodingGopher — Bounded First Slice Evaluation

> Date: 2026-04-20 | Pattern: `memory/work/large-extract-pattern.md` (Phase 2 bounded slice + Phase 3 evaluate)
> Scope: `tools/scratch/gopher_eval.md` only — no writes to `memory/knowledge/`.
> Channel: https://www.youtube.com/@TheCodingGopher — 153 total videos enumerated (metadata in `gopher_playlist.json`, top 5 in `gopher_top5.json`).

## Methodology

1. Enumerate: `yt-dlp --flat-playlist -J` → 153 entries, all with `view_count` populated.
2. Select: top 5 by `view_count` (pure view-rank, per task spec).
3. Transcribe: `yt-dlp --write-auto-sub --sub-lang en --sub-format vtt` → VTT → plain text (`tools/scratch/gopher/<id>.txt`).
4. Keyword scan: `agent`, `harness`, `llm`, `claude`, `orchestration` (primary) + `mcp`, `rag`, `embedding`, `vector db` (secondary).
5. Overlap scan: tokens appearing ≥3× in transcript AND present anywhere in `memory/knowledge/ai-infra/*.md`.

Raw keyword + overlap counts: `tools/scratch/gopher_analysis.json`.

## Top 5 by Views — Evaluation Matrix

| # | ID | Title | Views | Words | Primary AI keyword hits | Signal | Recommendation |
|---|----|-------|------:|------:|------------------------|--------|----------------|
| 1 | `D26sUZ6DHNQ` | 99% of Developers Don't Get Sockets | 525,704 | 2,045 | none | MED | stop (for AI-infra). Related: networking sub-domain (OS I/O primitives); flag only. |
| 2 | `oGPjzCBZGzg` | Docker vs. Kubernetes | 358,179 | 901 | orchestration×3 (container orchestration, not agent) | LOW | stop — 901 words is thin; `ai-infra/_context.md` already references Docker Compose usage. |
| 3 | `TdondBmyNXc` | I replaced my entire stack with Postgres... | 322,985 | 2,011 | claude×1, vector db×2 | HIGH | route-to-existing → `memory/knowledge/ai-infra/` (Postgres-as-unified-backend pattern; pgvector for agent memory). |
| 4 | `P8rrhZTPEAQ` | 99% of Developers Don't Get PostgreSQL | 236,749 | 2,145 | embedding×1 | MED | route-to-existing → `memory/knowledge/ai-infra/` (MVCC / WAL / TOAST internals; supports Postgres-as-state-store decision). |
| 5 | `KLW9gDP6nN8` | How Dynamic Programming Broke Software Engineers | 103,461 | 1,456 | none | LOW | stop — pure algorithms/interview content, zero Jarvis relevance. |

## Per-Video Signal Notes

### 1. `D26sUZ6DHNQ` — Sockets (MED / stop for ai-infra)
- Zero primary AI keywords; overlap with ai-infra corpus is generic (`server`, `client`, `data`, `network`, `file`, `port`).
- Technically relevant to async runtime substrate (epoll/kqueue, UDS for local Postgres, TLS for remote MCP-over-HTTP+SSE), but that is a *networking* concern, not an AI-infra one.
- **Overlap with ai-infra domain: low (incidental vocabulary only).**
- Recommendation: **stop** for this corpus. If promoted later, route to a `networking/` sub-domain — **do not** pollute `ai-infra/`.

### 2. `oGPjzCBZGzg` — Docker vs. Kubernetes (LOW / stop)
- `orchestration` hits are all container-orchestration, not agent-orchestration; no `agent`, `llm`, `claude`, `harness`.
- Only 901 transcript words — shallow introductory explainer.
- Overlap with ai-infra is shallow (`docker`, `deployment`, `scale`, `state`).
- **Overlap with ai-infra domain: low (surface-level vocabulary, no architectural insight).**
- Recommendation: **stop**. Container orchestration is not a gap in Jarvis knowledge.

### 3. `TdondBmyNXc` — I replaced my entire stack with Postgres (HIGH / route-to-existing)
- `claude×1`, `vector db×2`; overlap terms include `vector`, `index`, `search`, `query`, `database`, `neon` (directly echoes existing `ai-infra/_context.md`).
- Core thesis: collapse Redis / Kafka / ElasticSearch / vector DB into Postgres (LISTEN/NOTIFY, tsvector, pgvector). Directly relevant to Jarvis memory/state architecture.
- Caveat to capture: pattern breaks down at scale; "replace everything" is directional, not universal.
- **Overlap with ai-infra domain: HIGH (pgvector, LISTEN/NOTIFY, Postgres-as-state-store already explicit in the domain).**
- Recommendation: **route-to-existing** `memory/knowledge/ai-infra/` (Postgres-as-unified-backend note). **Do not create new sub-domain.**

### 4. `P8rrhZTPEAQ` — 99% Developers Don't Get PostgreSQL (MED / route-to-existing)
- 2,145 words on MVCC, WAL, page storage, transactions, versioning — strong overlap terms (`postgresql×20`, `write×16`, `ahead×16`, `transaction×16`, `versions×8`, `rows×9`, `pages×10`).
- Primary AI keywords are absent (one `embedding` mention is incidental). But the content explains *why* Postgres is the correct choice for Jarvis's agent state — supports decisions already recorded in `ai-infra/_context.md`.
- **Overlap with ai-infra domain: MEDIUM-HIGH (dedup risk: MVCC/WAL internals not yet in any ai-infra file — net-new supporting content).**
- Recommendation: **route-to-existing** `memory/knowledge/ai-infra/` (Postgres internals addendum). No new sub-domain.

### 5. `KLW9gDP6nN8` — Dynamic Programming (LOW / stop)
- Zero AI keywords. Overlap terms (`problem`, `optimal`, `dynamic`, `solution`, `table`) do not intersect Jarvis concerns.
- Classic LeetCode interview pedagogy; no architectural signal.
- **Overlap with ai-infra domain: none.**
- Recommendation: **stop**.

## Clustering Check

Top 5 by views does **not** form a coherent sub-domain:
- Networking (1) — sockets
- DevOps (1) — Docker/K8s
- Database internals (2) — Postgres × 2
- Algorithms (1) — DP

Two of five cluster into an existing domain (`ai-infra/`, Postgres angle). Three are orthogonal and low-signal.

## Selection-Criteria Caveat

The channel's AI-targeted content sits outside top-5-by-views. From `gopher_playlist.json`, AI-relevant titles and their ranks by views:

| AI-relevant candidate | Views | View rank |
|-----------------------|------:|----------:|
| Model Context Protocol (MCP) Explained | ~85K | ~#7 |
| LLMs Explained | ~10K | lower |
| Meta's AI Agent | ~5K | lower |
| 99% of Devs Don't Get DeepAgent | ~3K | lower |
| How RAG Changed The World | ~1K | lower |
| Vector Databases: The Secret Weapon for AI Search | ~1K | lower |

Pure view-rank selection missed all of these on this pass. Per `large-extract-pattern.md` Phase 2 guidance, future expansions on this channel should use **top 5 by views OR top 3 by AI-keyword match**, not view-count alone.

## Overall Recommendation

| Dimension | Verdict |
|-----------|---------|
| Stop extracting from this channel? | **No** — 2/5 videos carry ai-infra-relevant signal; AI-targeted long tail is richer than the viral head. |
| Create a new sub-domain for TheCodingGopher content? | **No** — high-signal content clusters into existing `memory/knowledge/ai-infra/` (Postgres / MCP) and possibly a lightweight `networking/` sub-domain. |
| Route signal to existing domain? | **Yes** — `ai-infra/` is the home for videos 3 and 4. |
| Expand bounded slice further? | **Yes — targeted.** Next slice should be AI-keyword-filtered (MCP, RAG, DeepAgent, Vector Databases, LLMs Explained), not the next 5 by views. |

**Net decision: ROUTE-TO-EXISTING (ai-infra) + EXPAND-SLICE (AI-keyword-filtered). No new sub-domain.**

## Deferred Actions (not executed per task scope)

Per task spec, this file is the only deliverable. The following would be executed on a subsequent, explicitly-scoped run:

- Write Postgres-stack signal (`TdondBmyNXc`) to `memory/knowledge/ai-infra/…postgres-unified-backend.md`.
- Write PostgreSQL internals signal (`P8rrhZTPEAQ`) as a supporting note or append to the same file.
- Schedule AI-keyword-filtered slice (MCP, RAG, DeepAgent, LLMs Explained, Vector Databases) as the next bounded batch (≤5).
- Patch `memory/work/large-extract-pattern.md` "Use log" with this 2026-04-20 confirming run (frequency gate → pattern promotable to `/create-pattern` skill after this second use).

## Targeted Expand Slice — AI-Keyword-Filtered (2026-04-20)

Executed to generate additional validation data for the bounded-slice pattern (rather than defer pattern promotion). Selected the 4 AI-keyword-matching videos not already extracted in the 2026-04-19 run. (MCP Explained `rCBSQxQr9Xg` and DeepAgent `E6Ip5xHpbYo` were excluded — already covered by `ai-infra/2026-04-19_mcp-protocol.md`.)

| # | ID | Title | Views | Words | Primary AI keyword hits | Signal | Recommendation |
|---|----|-------|------:|------:|------------------------|--------|----------------|
| 6 | `Kq8Iz9tTcSo` | Large Language Models (LLMs) Explained | 9,600 | 2,125 | llm×13, agent×2, claude×2, embedding×1 | HIGH | route-to-existing → `ai-infra/` (LLM fundamentals primer; supports `_context.md` citations). |
| 7 | `j3RmMc9wkbM` | Meta now has the most insane AI agent | 4,994 | 1,518 | agent×2, orchestration×2, embedding×2, llm×1 | MED | route-to-existing → `ai-infra/` (Meta-specific; note as vendor-flavored survey). |
| 8 | `IieuQlnrgT8` | How RAG Changed The World (In 2025) | 1,280 | 705 | rag×15, llm×5, vector db×2 | MED-HIGH | route-to-existing → `ai-infra/` (thin transcript but concentrated RAG signal; ideal as short definitional appendix). |
| 9 | `Ps913CUN1Tw` | Vector Databases: The Secret Weapon for AI Search | 883 | 1,142 | vector db×10, embedding×2 | HIGH | route-to-existing → `ai-infra/` (directly supports pgvector decisions; index types, similarity metrics). |

### Per-Video Signal Notes (expand slice)

- **`Kq8Iz9tTcSo` — LLMs Explained (HIGH)**: 2,125 words of clean fundamentals (tokens, next-token prediction, training regimes, human-in-the-loop). Strong overlap vocabulary with `ai-infra/_context.md` (`model×26`, `token×14`, `training×7`). Not net-new architecture but excellent primer for cross-linking.
- **`j3RmMc9wkbM` — Meta AI Agent (MED)**: Covers Meta's agent stack; useful as survey datapoint but heavily vendor-flavored. Overlap terms are generic (`action×10`, `state×6`). Downstream value: competitive context for `autonomous-coding-agents` file, not new architecture.
- **`IieuQlnrgT8` — RAG (MED-HIGH)**: Only 705 words — shortest transcript in the whole corpus — but RAG density is high (`rag×15` in 705 words ≈ 2.1%). Overlap includes `retrieval×5`, `external×10`, `fine-tuning×7` — directly relevant to Jarvis's embedding/retrieval stack. Ideal as a compact definitional note, not a full architecture doc.
- **`Ps913CUN1Tw` — Vector Databases (HIGH)**: Best architectural signal of the expand slice. `vector×29`, `similarity×8`, `indexing×8`, `databases×8` — aligns precisely with `ai-infra/` pgvector decisions. Covers HNSW, IVF, cosine vs dot-product — all referenced but not explained in existing files.

### Expand-Slice Conclusion

- 4/4 expand-slice videos have **route-to-existing** recommendation into `ai-infra/`.
- 0/4 justify a new sub-domain.
- Confirms the 2026-04-19 decision and the pattern's selection-criterion lesson (AI-keyword filter > pure view-rank).
- No writes to `memory/knowledge/` in this session — routing recommendations queued for the overnight dispatcher (batch-mode from `large-extract-pattern.md`).

## Pattern Promotion Readiness

Based on `.claude/skills/create-pattern/SKILL.md` Skill Lifecycle Gate + CLAUDE.md frequency gate:

| Check | Status | Notes |
|-------|--------|-------|
| 1. Can this be a `--flag` on an existing skill? | **Partial-no** | `/research` is query-driven; `/absorb` is single-artifact. Bounded-slice-then-evaluate on a large corpus doesn't map cleanly to either. Most likely home would be a new `--corpus` flag on `/research`, but the overnight dispatcher integration pushes this past flag scope. |
| 2. Architecture-review run? | **Not yet** | Required because the pattern touches external APIs (YouTube) and triggers autonomous writes to `memory/knowledge/`. Must run `/architecture-review` before promotion. |
| 3. Recurrence ≥ 4x in next 12 months? | **Likely YES** | TheCodingGopher (done 2×), Karpathy (in-flight), plus 2+ candidate channels on `sources.yaml`. Also generalizes to podcasts and paper sets. Base-rate projection: 6–10 uses/year. |
| 4. Promotion trigger + retirement trigger defined? | **Missing** | Must be added to the SKILL.md before shipping. |
| Frequency gate (monthly) | **Borderline** | 6–10/yr ≈ below monthly. Current SKILL.md load cost should be weighed against `--corpus` flag on `/research`. |
| 2nd confirming use on *different* corpus | **PENDING** | Karpathy Phases 2–4 are the blocking evidence. Today's TheCodingGopher re-run confirms stability on the same corpus — necessary but not sufficient. |

**Net**: not yet promotable. Gating items below.

### Minimum path to `/create-pattern` promotion

1. Complete **Karpathy Phases 2–4** end-to-end (overnight dispatcher already queued) — this is the 2nd-confirming-use on a fresh corpus.
2. Run **`/architecture-review`** on the pattern (3-agent review: first-principles + fallacy + red-team).
3. Run **`/second-opinion`** specifically on the `--flag`-vs-standalone question (answer likely: standalone, because overnight dispatcher integration is cross-skill).
4. Add **promotion + retirement triggers** to `memory/work/large-extract-pattern.md` before converting it into SKILL.md form.
5. Define **deterministic script split** per the `/create-pattern` design principle: `yt-dlp` + VTT-cleanup + keyword/overlap scan should live in `tools/scripts/` (not SKILL.md); only the Phase 3 evaluation and Phase 4 decision need the model.

Today's 2026-04-20 run satisfies none of 1–4 on its own but contributes (a) the 2nd proof of pattern stability and (b) a worked example for the promotion package.

## Scratch cleanup

Raw VTT + cleaned TXT for all 9 videos (~670 KB) are duplicates of the transcripts already captured in `memory/work/thecodinggopher/transcripts.json` + this eval's `gopher_analysis.json` / `gopher_expand_analysis.json`. Safe to delete after review.

## Artifacts in `tools/scratch/`

- `gopher_playlist.json` — full channel metadata (153 entries, UTF-8).
- `gopher_top5.json` — selected top 5 by views.
- `gopher_analysis.json` — top-5 per-video keyword + overlap counts.
- `gopher_expand_analysis.json` — expand-slice (4 AI videos) counts.
- `gopher/<id>.en.vtt`, `gopher/<id>.txt` — raw + cleaned transcripts (9 videos).
- `_select_top5.py`, `_vtt_to_text.py`, `_find_ai_videos.py`, `_analyze_expand.py` — reproducibility scripts.
