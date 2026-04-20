# Karpathy Corpus — Evaluation

> Phase 2 stub — dispatcher fills this file after each extraction batch.

## Corpus

- **Channel**: @AndrejKarpathy
- **URL**: https://www.youtube.com/@AndrejKarpathy/videos
- **Total videos**: 17
- **Queue size**: 12 (5 excluded: stable diffusion visual clips, no transcript value)
- **Phase 1 complete**: 2026-04-19

## Phase 1 — Video Inventory

| Priority | ID | Title | Duration | Views (approx) |
|---|---|---|---|---|
| 1 | 7xTGNNLPyMI | Deep Dive into LLMs like ChatGPT | 3:31:24 | 6.1M |
| 2 | zjkBMFhNj_g | [1hr Talk] Intro to Large Language Models | 59:48 | 3.6M |
| 3 | EWvNQjAaOHw | How I use LLMs | 2:11:12 | 2.4M |
| 4 | zduSFxRajkE | Let's build the GPT Tokenizer | 2:13:35 | 1.1M |
| 5 | l8pRSuU81PU | Let's reproduce GPT-2 (124M) | 4:01:26 | 1.1M |
| 6 | kCc8FmEb1nY | Let's build GPT: from scratch, in code, spelled out. | 1:56:20 | — |
| 7 | VMj-3S1tku0 | The spelled-out intro to neural networks and backpropagation: building micrograd | 2:25:52 | — |
| 8 | PaCmpygFfXo | The spelled-out intro to language modeling: building makemore | 1:57:45 | — |
| 9 | TCH_1BHY58I | Building makemore Part 2: MLP | 1:15:40 | — |
| 10 | P6sfmUTpUmc | Building makemore Part 3: Activations & Gradients, BatchNorm | 1:55:58 | — |
| 11 | q8SA3rM6ckI | Building makemore Part 4: Becoming a Backprop Ninja | 1:55:24 | — |
| 12 | t3YJ5hKiMQ0 | Building makemore Part 5: Building a WaveNet | 56:22 | — |

**Excluded** (stable diffusion timelapse clips, no educational transcript):
- kVpDARqZdrQ, 2oKjtvYslMY, sM9bozW295Q, vEnetcj_728, Jv1ayv-04H4

## Phase 2 — Extraction Results

> Dispatcher fills below. One section per batch.

<!-- BATCH_RESULTS_START -->
<!-- BATCH_RESULTS_END -->

## Phase 3 — Signal Summary

> Filled after all batches complete.

- **Signal quality**: TBD
- **Routing decision**: TBD (expected: `existing:ai-infra/` — deep LLM internals, training loops, tokenization)
- **Dedup risk**: MEDIUM — significant overlap expected with `harness-engineering.md` + `autonomous-coding.md` on LLM architecture; unique value likely in implementation-level details (BPE tokenizer, GPT-2 training loop, backprop mechanics)

## Phase 4 — Decision

> Filled after Phase 3 complete.

- [ ] Stop
- [ ] Scale with existing home
- [ ] New sub-domain
- [ ] Expand slice

## Pattern Promotion Gate

- Second successful corpus run clears CLAUDE.md frequency gate → promote to `/create-pattern`
- Gate: **Phase 4 complete** for this corpus
