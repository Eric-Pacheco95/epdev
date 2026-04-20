---
source: YouTube — Andrej Karpathy "Deep Dive into LLMs like ChatGPT"
video_id: 7xTGNNLPyMI
extracted: 2026-04-19
signal: MEDIUM
routing: ai-infra → harness-engineering.md supplement
dedup_note: harness-engineering.md has 'March of Nines' + per-step compute. Net-new: tool-use token-stream mechanics + RL vs SFT routing distinction.
---

# Karpathy — Deep Dive LLMs: Architectural + Routing Signal

## Tool Use Mechanics (how inference-time tool calls actually work)

- Tool use = special tokens injected into the generation stream (`search_start`/`search_end`); inference runner **pauses** on the end-token, executes the tool, pastes result into context window, then resumes — the LLM never "calls" tools directly
- Hallucination mitigation via search: model must be trained on correct tool invocation examples — a few thousand SFT examples suffice to establish the behavior reliably
- Context window is working memory: pasting source text directly is always higher quality than parametric recall — prefer RAG-style injection over asking the model to "remember" for factual tasks

## RL vs SFT Model Routing (dispatcher routing implication)

- RL/thinking models (o1, o3, DeepSeek R1) are **categorically different** from SFT models (GPT-4o, Claude Sonnet base): thinking models run internal multi-step chains before answering; SFT models imitate labeler responses
- **Routing rule**: complex multi-step reasoning → thinking model; factual/knowledge/formatting → SFT model
- SFT data quality bottleneck: human labelers cannot write ideal token sequences for problems where LLM knowledge exceeds human expert knowledge — RL lets the model discover its own optimal reasoning paths

## Compute Architecture (chain-of-thought as necessity)

- Per-token compute is fixed and finite: models cannot do arbitrary reasoning in a single forward pass — chain-of-thought is not a style choice, it is a **computational necessity** to distribute work across tokens
- Tokenization root cause: models see token IDs not characters; always offload character-level tasks (counting, regex, spelling) to code interpreter — never expect correct mental arithmetic on characters

## Hallucination Mitigation Patterns

- Pattern 1: interrogate model 3-5× on the same factual question; if answers diverge, add "I don't know" example to SFT data for that question type — trains uncertainty refusal without blanket refusals
- Pattern 2: explicit search tokens + context injection (see tool use mechanics above)
