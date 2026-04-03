# Signal Synthesis -- 2026-04-03
- Signals processed: 30
- Failures reviewed: 2
- Period: 2026-04-02 to 2026-04-03

---

## Themes

### Theme: Architecture review is the proven overengineering guard
- Maturity: proven
- Confidence: 95%
- Anti-pattern: false
- Supporting signals: 2026-04-02_arch-review-convergence-value.md, 2026-04-03_arch-review-overengineering-guard.md, 2026-04-02_status-as-execution-guard.md, 2026-04-03_dont-build-for-theoretical-gaps.md, 2026-04-03_real-gap-vs-theoretical-gap.md, 2026-04-03_feedback-loop-asymmetry.md
- Prior synthesis: "Architecture-review gate is validated and working" (established, 85%) -- UPGRADED
- Failure weight: 0
- Pattern: Across 4 separate architecture reviews (local embeddings, /backlog, /make-prediction, and dispatcher budget), the parallel 3-agent pattern consistently (a) caught overengineering, (b) converged on non-obvious structural findings, and (c) produced better architecture than the original proposal. The /make-prediction review corrected 5 structural assumptions (3 engines -> 2 layers, 6 steps -> 4, dropped BDM tables, dropped bias checklist, dropped /extract-alpha chain). The /backlog review caught a Goodhart violation and a flippable boolean guard. The convergence pattern (3 agents independently finding the same issue) is a high-confidence signal.
- Implication: /architecture-review is no longer "validated" -- it is proven infrastructure. The research phase naturally proposes maximum complexity; arch review prunes to what works. This is especially important given Eric's ADHD build velocity.
- Action: Upgrade steering rule confidence. No rule change needed -- existing rule is correct. Promote to proven maturity.

---

### Theme: Unified pipeline vision is the architectural north star
- Maturity: established
- Confidence: 85%
- Anti-pattern: false
- Supporting signals: 2026-04-02_unified-pipeline-vision-articulated.md, 2026-04-02_overnight-as-producer.md, 2026-04-02_two-stage-gate-pattern.md, 2026-04-02_status-as-execution-guard.md, 2026-04-03_capability-tracks-tasklist-pattern.md
- Failure weight: 0
- Pattern: Eric articulated the full pipeline vision: ALL work from ANY source flows through one system (backlog -> gates -> dispatch -> execution -> learning). The overnight runner was correctly reframed as a producer (emitting backlog tasks) rather than a participant (sharing the dispatcher execution model). The two-stage gate (write-time + dispatch-time) was independently validated by 3 agents. Status-based gating (pending_review vs boolean flags) was identified as defense-in-depth. Capability tracks extend this with dependency-triggered resurfacing.
- Implication: Every new feature must ask "does this flow through the unified pipeline?" Before building any standalone system, evaluate whether it should be a producer that emits backlog tasks instead. The producer pattern (do your thing, emit backlog task as output) is the integration protocol.
- Action: Already captured in memory as project_unified_pipeline_vision.md. No new steering rule needed -- this is project-level architectural principle, not a behavioral rule.

---

### Theme: Investment research pipeline is a validated alpha-generation method
- Maturity: established
- Confidence: 80%
- Anti-pattern: false
- Supporting signals: 2026-04-03_invalidate-pivot-alpha-method.md, 2026-04-03_multi-hop-causal-chain-validated.md, 2026-04-03_research-pipeline-skill-chain.md, 2026-04-03_options-as-time-isolation.md, 2026-04-02_ai-bubble-datacenter-delays.md
- Failure weight: 0
- Pattern: The /absorb > /extract-alpha > /analyze-claims > invalidate > re-extract pipeline was executed end-to-end in a single session. Key finding: the willingness to kill a thesis AFTER verification (not before) is the edge. Nuclear/uranium looked strong from /extract-alpha but /analyze-claims revealed CCJ at 111x P/E and inflated uranium claims. Re-extraction from the same data found better risk/reward in adjacent markets (grid equipment, BESS, copper). The multi-hop causal chain model (Iran > Hormuz > LNG > energy > datacenter > grid > transformers > copper) found alpha at hop 4-6 where the crowd hadn't arrived. Eric uses options as time-isolation instruments to match known catalyst dates.
- Implication: This pipeline should be documented as the canonical investment research workflow. /extract-alpha outputs should include catalyst calendars with dates, and proactively suggest options structures mapping to those dates. Consider creating a composite skill (/investment-thesis) that orchestrates the chain.
- Action: Candidate for new skill: /investment-thesis as orchestrator of the absorb > extract > verify > invalidate > re-extract chain. Score: Recurrence=High (Eric does this weekly+), Repeatability=High (same chain each time), Value=High (saves 30+ min and catches thesis errors). Surface as skill gap candidate.

---

### Theme: Test isolation for stateful writes is a recurring gap
- Maturity: established
- Confidence: 80%
- Anti-pattern: false
- Supporting signals: 2026-04-02_self-test-state-pollution.md, 2026-04-02_smoke-test-side-effects.md, 2026-04-02_rate-limit-silent-success.md
- Failure weight: 0 (bugs, not failures -- caught before deployment)
- Pattern: Three instances of the same class of bug in 48 hours: (1) overnight runner self-test overwrote production overnight_state.json, (2) routines smoke test wrote to real task_backlog.jsonl, (3) rate-limited claude -p returned exit code 0, causing false success in both overnight runner and dispatcher. All three involve stateful side effects leaking from test/error contexts into production state.
- Implication: Self-tests, smoke tests, and error-handling paths must ALL use isolated paths for EVERY stateful write. Exit code 0 is not sufficient to confirm real work was done for claude -p consumers. These are the same class of bug -- the "test/error boundary" that should isolate side effects is missing or incomplete.
- Action: Propose steering rule about test isolation. See Proposed Steering Rules below.

---

### Theme: Eric's operator style requires zero-friction safety
- Maturity: established
- Confidence: 85%
- Anti-pattern: false
- Supporting signals: 2026-04-02_multi-terminal-git-risk.md, 2026-04-02_zero-habit-guardrails.md, 2026-04-02_teach-then-redirect.md, 2026-04-02_phased-trust-shipping.md, 2026-04-02_model-tiered-delegation.md, 2026-04-02_budget-from-usage-data.md
- Failure weight: 0
- Pattern: Eric runs 4+ parallel terminals on main, prefers passive warnings over workflow changes, chooses the lightest guardrail option, asks "the real question" behind the stated question (operator risk, not infrastructure risk), values phased trust-gradient shipping, and is building muscle memory for model-tiered delegation (Opus=judgment, Sonnet=code, Haiku=config). Operational limits should be derived from measured data, not theoretical planning.
- Implication: Safety features and guardrails must add zero cognitive overhead. Hooks that surface context at the right moment (session-start banner) are the sweet spot. When Eric frames infrastructure questions, probe whether the concern is about himself as operator. Present options before recommendations. Derive budgets from usage data.
- Action: Most of these are already captured as user/feedback memories. No new steering rule -- this is a reinforcing cluster confirming existing patterns.

---

### Theme: Full skill development chain validated
- Maturity: candidate
- Confidence: 70%
- Anti-pattern: false
- Supporting signals: 2026-04-03_full-skill-dev-chain-validated.md, 2026-04-03_llm-self-audit-impossible.md
- Failure weight: 0
- Pattern: First complete execution of /research -> /architecture-review -> /create-prd -> /implement-prd -> test -> /backlog -> capability track. The chain consumed one full context window. LLM self-audit was identified as architecturally impossible -- user-facing interrogation questions are the correct replacement. Self-reflection steps in skills should be replaced with adversarial agent patterns or user interrogation.
- Implication: This is the reference pattern for building new skills. Budget one full context window per skill build. Run /learning-capture before test runs to avoid losing signals to compaction. The "LLM cannot audit itself" insight should be applied retroactively to any skill with a self-check step.
- Action: Candidate -- needs 1-2 more skill builds to confirm the pattern holds. Audit existing skills for self-audit steps that should be replaced with interrogation questions.

---

### Theme: System health noise from heartbeat auto-signals
- Maturity: established
- Confidence: 65%
- Anti-pattern: false
- Supporting signals: 2026-04-03_heartbeat-network_connections.md, 2026-04-03_heartbeat-network_connections_2.md, 2026-04-03_heartbeat-network_connections_3.md, 2026-04-03_heartbeat-network_connections.md (unprocessed, 73% spike), 2026-04-03_heartbeat-network_connections_2.md (unprocessed, 58% spike), 2026-04-03_heartbeat-context_budget_proxy.md (unprocessed, 9.8% increase)
- Failure weight: 4 (1 failure: autoresearch runner failed x4)
- Pattern: 6 heartbeat auto-signals generated on 2026-04-03 alone -- 5 network_connections WARNs and 1 context_budget_proxy WARN. The network_connections signals report spikes of 55%, 73%, and 58% across multiple heartbeat windows, while context_budget_proxy reported a 9.8% increase. All are low-information: they confirm metrics changed but provide no root cause and suggest only "review and consider adjusting thresholds." The context_budget_proxy signal extends the pattern beyond network_connections to a second metric, confirming this is a systemic noise problem with the heartbeat auto-signal producer, not specific to one metric.
- Implication: Heartbeat auto-signals need both deduplication and threshold recalibration. The "same metric, same direction" dedup rule should suppress repeats within 24h. Network connections increasing 55-73% with multiple concurrent Claude sessions is expected behavior and should not trigger WARN. The context_budget_proxy 9.8% increase is well within normal variance and should not trigger either. The auto-signal producer is generating noise that pollutes the synthesis pipeline -- 6 of the unprocessed signals today (100%) are low-information heartbeat WARNs.
- Action: (1) Raise min_delta thresholds in heartbeat_config.json for network_connections (current threshold too low for multi-session workloads). (2) Add 24h same-metric dedup window. (3) Consider adding context correlation (session count) to suppress expected spikes. Upgraded to established: 6 signals across 2 metrics confirm the noise pattern.

---

### Theme: YouTube content extraction remains a gap
- Maturity: candidate
- Confidence: 60%
- Anti-pattern: false
- Supporting signals: 2026-04-03_youtube-transcript-extraction-gap.md
- Failure weight: 0
- Pattern: tavily_extract, WebFetch, and tavily_search all fail to extract YouTube video transcripts. The workaround (search for corroborating coverage of the video topic) works but costs 2-3 extra tool calls.
- Implication: For /absorb on YouTube, skip direct transcript extraction and go straight to corroborating source search. A YouTube transcript MCP server (yt-dlp based) would solve this but the workaround is adequate for now.
- Action: Candidate only. If YouTube content frequency increases, evaluate yt-dlp MCP server. For now, document the workaround in /absorb or /research skill notes.

---

## Proposed Steering Rules

1. **PROMOTE (established, 3 supporting signals)**: Self-tests, smoke tests, and ad-hoc inline validation must redirect ALL stateful write paths to temporary files -- not just the primary file under test, but every side-effect path (state files, backlogs, lock files). For claude -p consumers, check stdout for rate limit messages before interpreting results; exit code 0 does not confirm real work was done.

   Proposed CLAUDE.md section: Workflow Discipline
   Draft rule: "Self-tests and smoke tests must use isolated paths for ALL stateful writes, not just the primary target -- state files, backlogs, and lock files all need temp paths; additionally, any claude -p consumer must check stdout for rate limit messages before treating exit code 0 as success"

2. **UPGRADE (proven, 5+ signals across 4 reviews)**: Architecture review gate is now proven infrastructure. No rule change needed -- existing steering rule is correct and working. Confidence: 95%.

3. **REVALIDATE from prior synthesis**: "System self-diagnosis fails silently under rate limiting" (candidate, anti-pattern) -- now supported by rate-limit-silent-success signal. Still candidate but confidence rises to 80%. One more occurrence should trigger promotion.

---

## Proposed TELOS Updates

1. **MODELS.md update candidate**: The multi-hop causal chain model was validated in a live investment research session (Iran > Hormuz > LNG > energy > datacenter > grid > copper). If this model was added to MODELS.md during the session, no action needed. If not, it should be added as a validated analytical framework.

2. **STRATEGIES.md consideration**: The invalidate-and-pivot alpha method (/absorb > /extract-alpha > /analyze-claims > invalidate > re-extract) is a repeatable investment strategy that deserves documentation alongside other strategies.

---

## Confidence Decay Review

| Theme | Previous maturity | New maturity | Last signal date | Reason |
|-------|-------------------|--------------|------------------|--------|
| Architecture-review gate validated | established (85%) | proven (95%) | 2026-04-03 | 3 new supporting signals across 2 sessions |
| Grep failure blindness | candidate (70%) | candidate (65%) | 2026-04-02 | No new signals, slight confidence decay but within 90d |
| Autonomous producer health degrading | candidate (60%) | candidate (55%) | 2026-04-03 | Heartbeat WARNs provide weak support; likely benign (14 sessions open) |
| System self-diagnosis fails silently | candidate (75%) | candidate (80%) | 2026-04-02 | Rate-limit-silent-success signal supports the pattern |

---

## Anti-Patterns

### Anti-Pattern: Treating "no documented failures" as proof of sufficiency (REVALIDATED)
- Anti-pattern: true
- Maturity: candidate (held from prior synthesis)
- Applies to: grep sufficiency evaluation, self-diagnose empty response handling, exit code 0 interpretation
- New evidence: rate-limit-silent-success signal shows exit code 0 masking total failure -- same epistemological class as "no grep failures means grep is fine"
- Rule: Absence of evidence is not evidence of absence. For measurement-dependent systems, ask: "could failures be invisible to this measurement method?"

### Anti-Pattern: LLM self-audit creates false confidence (NEW)
- Anti-pattern: true
- Maturity: candidate
- Applies to: any skill with a "check your biases" or "self-review" step
- Evidence: /make-prediction arch review identified that LLM bias checklists generate plausible-sounding self-critique without detecting real biases
- Rule: Replace LLM self-reflection steps with either adversarial agent patterns (separate agent attacks the output) or user-facing interrogation questions. Self-reflection is theater; adversarial review and user challenge are real.

---

## Meta-Observations

1. **Signal velocity jumped dramatically.** From 0.86/day (prior synthesis) to 4.71/day. This is driven by two long, productive sessions (5C pipeline work + investment research + /make-prediction skill build) plus heartbeat auto-signals. The velocity will normalize. The synthesis threshold of 20 signals was correctly triggered.

2. **Heartbeat auto-signals are low-information noise.** 3 of 27 signals (11%) are identical network_connections WARNs that add no insight. The min_delta threshold for network_connections should be raised, or the dedup window extended, to prevent polluting the synthesis pipeline with noise. Auto-signals are valuable when they surface real degradation; these were expected behavior from 14 concurrent Claude sessions.

3. **Investment/domain signals are the highest quality.** The 5 investment research signals (avg rating 8.0) are significantly higher quality than system-health signals (avg rating 6.0). This makes sense -- domain insights from Eric's active work sessions carry more long-term learning value than transient system metrics. The learning system is doing its job when domain signals outnumber infrastructure signals.

4. **Cross-session signal correlation is emerging.** The architecture review theme now spans 4 separate reviews across 3 sessions. The test isolation theme spans 3 bugs across 2 sessions. These multi-session patterns are exactly what synthesis is designed to detect -- individual signals that only become visible as a pattern when aggregated.

5. **First skill gap candidate detected.** The investment research pipeline (/absorb > /extract-alpha > /analyze-claims > invalidate > re-extract) scores High on all three criteria (recurrence, repeatability, value). This is the strongest skill gap candidate since /make-prediction itself.
