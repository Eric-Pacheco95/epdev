# Overnight Run Report: prompt_quality -- 2026-04-04

## Summary

- **Dimension**: prompt_quality
- **Branch**: jarvis/overnight-2026-04-04
- **Baseline**: 47,868 words
- **Final**: 44,498 words
- **Delta**: -3,370 words (-7.0%)
- **Iterations**: 15 / 15 max
- **Kept**: 15 | **Discarded**: 0

## Strategy

Three primary reduction patterns applied:

1. **CONTRACT section deduplication** (11 skills, ~-859 words): Skills had `## Input` and `## Output` under `# CONTRACT` that fully duplicated their `# DISCOVERY > Output Contract`. Removed with zero information loss.

2. **Deprecated skill cleanup** (2 skills, ~-1,605 words): `voice-capture` and `label-and-rate` retained full original skill bodies as "archived" text never loaded in active sessions. Stripped to deprecation notices only.

3. **Prose tightening** (6 skills, ~-906 words): Verbose multi-line bullet lists condensed to compact single-line format in `make-prediction`, `extract-harness`, `research`, `absorb`, `jarvis-help`. All analytical content preserved.

## TSV Run Log

iteration	commit_hash	metric_value	delta	status	description
baseline	3a9b46d	47868	--	--	pre-run baseline
1	d189dc4	47773	-95	KEPT	implement-prd: remove duplicate CONTRACT Input/Output
2	0cd53ea	47639	-134	KEPT	learning-capture: remove duplicate CONTRACT Input/Output
3	00bf528	47009	-630	KEPT	9 skills: remove duplicate CONTRACT Input/Output (batch)
4	0e943fd	46956	-53	KEPT	make-prediction: condense Named Heuristics to single-line
5	c6d262a	46866	-90	KEPT	make-prediction: condense Market Lens to compact format
6	d697125	46734	-132	KEPT	extract-harness: condense adaptation checklists to prose
7	6cfe8f6	46722	-12	KEPT	research: condense OUTPUT FORMATS to table format
8	c55f4b9	46641	-81	KEPT	research: condense outreach security constraints
9	bf67093	46454	-187	KEPT	jarvis-help: remove redundant fallback stage-mapping table
10	22f28ae	45431	-1023	KEPT	voice-capture: strip archived deprecated content
11	0d51385	44849	-582	KEPT	label-and-rate: strip archived deprecated content
12	719be46	44692	-157	KEPT	make-prediction: condense geopolitics analytical pillars
13	5cfab6a	44618	-74	KEPT	absorb: condense SECURITY and ERROR HANDLING sections
14	8e9129f	44594	-24	KEPT	make-prediction: condense SECURITY RULES to 2 bullets
15	e970287	44498	-96	KEPT	extract-harness: condense EVOLVE gap-analysis section

## Quality Assessment

All reductions preserved every analytical framework, security rule, workflow logic step, skill chain, and output contract. Zero novel content removed -- only redundancy and archived dead code.

## Remaining Opportunities (future runs)

- make-prediction Step 5 TRACK: prediction record template ~150w compressible
- absorb Steps 7-8: TELOS proposal review workflow has dense prose
- research Phase 4.3: Slack staging steps have redundant safety labels
- learning-capture: signal format block + explanation ~100w of structural metadata
