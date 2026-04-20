---
source: YouTube — Andrej Karpathy "[1hr Talk] Intro to Large Language Models"
video_id: zjkBMFhNj_g
extracted: 2026-04-19
signal: MEDIUM
routing: ai-infra → harness-engineering.md supplement
dedup_note: harness-engineering.md already has 'March of Nines' reliability math. Net-new here: LLM-as-OS framing + security attack taxonomy.
---

# Karpathy — LLM Intro: Architectural + Security Signal

## LLM-as-OS Framing (Jarvis dispatcher relevance)

- Context window = RAM; internet/files = disk; kernel process = dispatcher/orchestrator coordinating tools
- Tool use is the primary capability axis: LLMs emit special tokens to invoke browser, calculator, Python, image gen — not attempt in-head computation
- Implication for Jarvis: dispatcher is the "kernel" — skill routing, context management, and tool invocation mirror OS resource management

## Capability Gaps (open research)

- System 1 vs System 2 gap: current LLMs only do fast instinctive next-token generation; "convert time into accuracy" via tree-of-thoughts is the unsolved direction
- Scaling law invariant: performance is a smooth function of N (parameters) × D (data) only — algorithmic progress is bonus, not a guarantee

## Training Architecture (orientation)

- Pre-training = knowledge compression (expensive: months, $2M+); result = base model with world knowledge but no alignment
- Fine-tuning = alignment/formatting layer (cheap: days, swappable dataset); does NOT add knowledge — it shapes behavior

## Security Attack Taxonomy (Jarvis constitutional rules gap)

- **Prompt injection via indirect retrieval**: LLM browsing attacker-controlled pages injects new instructions — applies to any Jarvis skill using Tavily/WebFetch on external content
- **Data poisoning / backdoor trigger**: fine-tuning on attacker-influenced data embeds trigger phrases that corrupt outputs — threat model for externally-sourced RAG corpora
- **Encoding jailbreak**: safety refusals trained mostly on English; Base64 or low-resource language encoding bypasses refusals — relevant to Jarvis prompt construction for safety-sensitive tasks
