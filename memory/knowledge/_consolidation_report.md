# Domain Knowledge Consolidation Report
> Generated: 2026-04-15 20:39 UTC

## Summary
- Domains processed: 9
- Article count (new): 54
- Sub-domains proposed: 4
- Taxonomy changes proposed: 1
- Contradictions detected: 30

## Domain Results

### ai-infra
- Article count (new this run): 19
- _context.md: 8000 chars
- Proposed sub-domains (1): `agent-orchestration.md`
- Contradictions:
  - The article frames the slowdown as a demand-correction while simultaneously citing capital overcommitment -- these are partially contradictory: demand-correction implies demand was always lower than projected, while capital overcommitment implies demand was real but misallocated in timing. The distinction matters for forecasting recovery timelines.
  - Prediction market mechanics (Article 4) is included in ai-infra domain but its primary application is forecasting/calibration, not infrastructure. The domain tag is defensible (Jarvis uses prediction as a capability) but may cause retrieval confusion; consider a prediction sub-domain tag or a cross-domain link.
  - Article 6 (2026-03-30_geo-strategy-iran-trap.md) is tagged domain=ai-infra but contains geopolitics content with no AI infrastructure relevance. Metadata tagging error -- route to geopolitics domain.
  - Article 2 argues scaffolding beats framework complexity (mini-SWE-agent 100 lines outperforms multi-agent systems) while Article 5 (Claude Managed Agents) presents a hosted runtime with rich built-in toolsets as the path forward. Not directly contradictory -- they sit at different points on the build-vs-buy spectrum -- but no reconciliation is provided across articles.
  - No direct contradictions detected across the 6 articles. Paperclip AI (Article 6) advocates for hierarchical multi-agent delegation while Article 3 (Emanuel) recommends deferring most multi-agent tooling until parallel session infrastructure is stable -- these are compatible (build infrastructure first, then delegate) but could be misread as opposing adoption timelines.
  - Article 4 (phase5-orchestration-patterns) concludes Jarvis should absorb patterns into its existing architecture rather than adopt new tools; Article 3 implies the prompt-first vs. CLI-first gap is fundamental enough that PAI's architecture is structurally superior -- if true, the 'absorb not adopt' conclusion from Article 4 may be unduly conservative.
  - Article 2 (harness-engineering) recommends hooks as the only reliable enforcement path, implying CLAUDE.md guidance is insufficient for critical behaviors; Article 3 (pai-v4-jarvis-comparison) treats the existing CLAUDE.md steering rule ('does this step require intelligence?') as a valid guide that just needs more consistent application -- these imply different root causes for the prompt-first gap (structural vs. discipline) and suggest different fixes (move logic to hooks vs. enforce the rule harder).
  - Mainstream 'bubble pop' framing conflicts with continued hyperscaler capex guidance (Microsoft, Google, Meta all raised 2025-2026 capex in earnings calls as of late 2025) -- either the delay data is capturing a subset of operators, or the capex guidance is forward-dated past the current bottleneck window.

### automotive
- Article count (new this run): 3
- _context.md: 2411 chars
- Contradictions:
  - Two of three articles submitted to the automotive synthesizer are off-domain (geopolitics: Iran Trap; AI/tech: datacenter delays) -- these articles carry no automotive content and should not have been routed here; no internal automotive contradictions detected in the on-domain article
  - The article positions BYD Seal as the best fit at $45K-$60K CAD, but also states Ioniq 6 wins at ~$41.8K -- these are not contradictory but the framing implies Seal competitiveness that only materializes if pricing lands at the low end of the estimate range

### crypto
- Article count (new this run): 3
- _context.md: 3720 chars
- Contradictions:
  - Article 3 (2026-03-30_geo-strategy-iran-trap.md) is tagged domain=geopolitics and contains no crypto content -- inclusion in a crypto synthesis batch is a routing error; excluded from all crypto knowledge output
  - Article 1 implies the Python/Freqtrade stack is mature and sufficient; Article 2 states Python is insufficient for competitive MEV and Rust is required -- these are compatible (different use cases) but the framing in each article does not acknowledge the other context, creating a misleading impression of Python adequacy if articles are read in isolation

### fintech
- Article count (new this run): 2
- _context.md: 2217 chars
- Contradictions:
  - Article 1 positions Canada as '#1 globally for AI maturity in banking', implying advanced adoption; Article 2 reports that globally only 4 of 50 largest banks show realized ROI and 95% of GenAI is in pilot -- these signals are in tension unless Canadian banks are disproportionately in the 4-bank ROI cohort, which is unverified.
  - Article 2 projects banking AI spend reaching $143-190B by 2030 (implying strong growth momentum) while simultaneously reporting near-zero production conversion rates -- high spend with minimal realized ROI suggests the growth projection may be based on budget allocation rather than outcome validation.

### general
- Article count (new this run): 1
- _context.md: 2606 chars
- Contradictions:
  - Source article was truncated -- the abiogenesis and biological evolution sections referenced in the topic title and tags were not present in the received fragment. Key findings may be incomplete. Do not treat the cosmology portion as a full representation of the article's scope.

### geopolitics
- Article count (new this run): 2
- _context.md: 3581 chars
- Contradictions:
  - Article 2 is categorized under geopolitics but its primary subject is domestic US tech investment trends -- the geopolitical framing (US-China AI race) is secondary and not fully developed in the available source material; its placement in this domain is inferential.
  - The Iran Trap article uses historical analogies to argue for a structural overextension trap, but the mechanism by which decision-makers repeat historically documented failures despite access to those case studies is not explained -- the argument implicitly assumes institutional amnesia without establishing it.

### predictions
- Article count (new this run): 20
- _context.md: 8000 chars
- Proposed sub-domains (3): `backtested-geopolitics.md`, `geopolitics-military-conflict.md`, `market-crypto.md`
- Contradictions:
  - Both predictions share identical primary_confidence (0.82) despite covering materially different domains (crypto protocol vs. macro policy) and difficulty ratings (medium vs. low). Identical confidence across different difficulty levels implies the confidence signal is not domain-calibrated.
  - Iran JCPOA: confidence 0.95 on a wrong outcome. Either the scoring model was overconfident, or leakage inflated the stated confidence, or the 2022-07-01 knowledge cutoff still contained enough negotiation trajectory signal to justify 0.95. The articles do not disambiguate which explanation applies.
  - Finland-Sweden NATO: confidence 0.92 (highest in cluster) paired with alignment score 0.417 (lowest in cluster) and suspect_leakage: true. If the prediction was high-quality and genuinely constrained, low alignment is unexpected. If leakage occurred, high confidence is artifactual. These two interpretations are mutually exclusive and cannot both be true.
  - mkt-crypto-bear-2022 outcome_label is 'wrong' but the known_outcome confirms the event DID occur (BTC fell below $20k). The contradiction is in the model's prediction direction, not the label -- the label correctly scores the model as wrong. No data integrity issue, but the metadata is ambiguous without reading the full article.
  - Saudi-Iran normalization: labeled outcome_label 'wrong' but the known_outcome confirms normalization DID occur (March 10 2023). The prediction was wrong about timing or mechanism, not occurrence. The 'wrong' label appears to conflict with the known_outcome text -- this discrepancy requires human review.
  - mkt-btc-halving-ath-2024 prediction asked whether BTC would reach ATH 'following the April halving' but the known outcome shows ATH occurred on March 14 -- before the halving. The prediction is scored 'correct' on price level but the causal framing (post-halving) was wrong. Alignment score (0.583) may not capture this timing error.
  - geo-us-election-2020 shows alignment_score 1.0 with primary_confidence only 0.52 -- perfect keyword alignment paired with near-coin-flip confidence suggests the model reproduced the correct vocabulary while remaining deeply uncertain about the outcome. This decoupling undermines alignment score as a confidence proxy.
  - mkt-eth-merge-2022 has alignment_score 0.588 (lower) but outcome_label 'correct'; mkt-fed-hikes-2022 has alignment_score 0.733 (higher) but outcome_label 'partial'. This inverts the expected correlation between alignment score and prediction accuracy, suggesting keyword-alignment-v1 does not reliably track correctness.
  - Brexit: primary_confidence=0.75 with alignment_score=0.40 -- the model was confident and correct, but prediction vocabulary poorly matched the outcome description; either the correct call was made via reasoning not captured by keyword overlap, or confidence was justified by a mechanism alignment scoring cannot measure
  - Iran trade plan (article 2) is explicitly conditioned on trump-iran-power-plant-strikes (article 3) resolving a specific way, but article 3 was 'open' at the same date as article 2 -- the trade plan was published as actionable before its geopolitical premise was confirmed, creating a dependency order violation in the prediction pipeline
  - French election: alignment_score=1.0 and suspect_leakage=true are in direct tension -- high alignment should increase calibration confidence, but leakage suspicion means that alignment is evidence of contamination, not skill; treating both signals as positive simultaneously is incoherent

### security
- Article count (new this run): 3
- _context.md: 3363 chars
- Contradictions:
  - Article 3 (2026-03-30_geo-strategy-iran-trap.md) is tagged domain: geopolitics in its frontmatter but was included in a security-domain synthesis batch. No internal contradiction within security articles, but the routing is an error -- geopolitics content should not influence security domain knowledge files.
  - Article 1 is truncated mid-sentence in the source material ('Direct -- Use') making it impossible to verify the complete two-forms-of-injection taxonomy. The synthesis relies on Article 2 for the complete model; Article 1 may have contained divergent detail.

### smart-home
- Article count (new this run): 1
- _context.md: 2722 chars

## Proposed Domain Retirements

### general -- retire
- Article count: 1
- Last article: 2026-03-27_evolution-big-bang.md (12 days old)
- Reason: general domain -- flag for retirement, redistribute articles
- Action: Remove CLAUDE.md routing entry; add RETIRED notice to index.md
- general domain articles need reassignment:
  - 2026-03-27_evolution-big-bang.md -> (assign to domain)
