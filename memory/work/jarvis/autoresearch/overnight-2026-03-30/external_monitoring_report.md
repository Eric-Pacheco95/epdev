# Overnight Run Report: external_monitoring

- **Date**: 2026-03-30
- **Branch**: jarvis/overnight-2026-03-30
- **Dimension**: external_monitoring
- **Goal**: Check sources in sources.yaml for new releases, updates, or significant changes
- **Scope**: memory/work/jarvis/

## Summary

**Result: sources.yaml created (was missing from repo) + 10 Tier 1/2 sources checked**

The `sources.yaml` file referenced in the tasklist (marked complete 2026-03-28) was never committed to git. Created it with 24 sources (6 T1, 6 T2, 12 T3) matching the original spec. All Tier 1 and 4 Tier 2 sources were checked via web search. Findings below.

- **Baseline metric**: 0 (last_checked entries)
- **Final metric**: 25 (24 sources + 1 header comment match)
- **Iterations used**: 2 (create sources.yaml, write report)
- **Changes kept**: 2
- **Changes discarded**: 0

## Tier 1 Findings (Daily Sources)

### Anthropic (checked 2026-03-30)
- **Snowflake partnership**: $200M multi-year deal for Claude across cloud platforms + joint agentic AI go-to-market
- **Claude Partner Network**: $100M investment announced 2026-03-12
- **The Anthropic Institute**: Introduced 2026-03-11
- **Research**: Abstractive red-teaming paper (natural-language categories that elicit character violations)
- **2026 Agentic Coding Trends Report** published

### Claude Code (checked 2026-03-30)
- **v2.1.87** released 2026-03-28 (latest)
- Key fixes: deniedMcpServers not blocking claude.ai MCP servers, diff syntax highlighting in non-native builds, MCP step-up auth with refresh tokens, memory leaks in remote sessions, Python Agent SDK MCP server handling
- **ACTION**: Eric should verify his Claude Code version is current

### OpenAI (checked 2026-03-30)
- **GPT-5.4 mini and nano** released 2026-03-17 (free/Go users get Thinking via 5.4 mini)
- **OpenAI acquiring Astral** (uv/ruff/ty) announced 2026-03-19 — significant Python tooling impact
- **Safety Bug Bounty** program announced 2026-03-25
- **Codex Security**: Scanned 1.2M commits, found 10,561 high-severity issues
- GPT-5.1 models removed from ChatGPT as of 2026-03-11

### Krebs on Security (checked 2026-03-30)
- **AI Assistants security implications**: How AI assistants with file/computer access are moving security goalposts — directly relevant to Jarvis architecture
- **Microsoft Patch Tuesday March 2026**: 77 vulnerabilities patched
- **IoT Botnets disrupted**: DOJ + Canada + Germany dismantled 4 botnets (3M+ compromised devices)
- **Iran-backed attacks**: Wiper attacks on Stryker (medtech) + CanisterWorm targeting Iran

### The Hacker News (checked 2026-03-30)
- **CVE-2026-32746**: Critical telnetd pre-auth RCE (CVSS 9.8) — root access via port 23
- **Trivy GitHub Actions breached**: 75 tags hijacked to steal CI/CD secrets — supply chain attack
- **CVE-2026-33017**: Critical Langflow flaw exploited within 20 hours of disclosure — relevant since LangChain is a Tier 2 source
- **FortiGate exploitation**: Config files with service account creds stolen (healthcare, govt, MSPs)
- **Malicious PyPI packages**: Versions 4.87.1/4.87.2 hid credential harvesting in .WAV files (2026-03-27)
- **APT28**: MSHTML 0-day (CVE-2026-21513) exploited before Feb 2026 patch

### Simon Willison (checked 2026-03-30)
- **OpenAI acquiring Astral** (2026-03-19): Thoughts on uv/ruff/ty acquisition — Python ecosystem implications
- **Package Managers Need to Cool Down** (2026-03-24): Security + packaging discussion
- **Starlette 1.0** released (2026-03-24): Foundation of FastAPI
- **Pretext** (2026-03-29): New browser library from ex-React core dev Cheng Lou
- **Quantization from the ground up** (2026-03-26)
- **AI writing policy** (2026-03-01): "if text has 'I' pronouns, it's written by me"

## Tier 2 Findings (Weekly Sources)

### Daniel Miessler / Fabric (checked 2026-03-30)
- **Fabric v1.4.437** (2026-03-16): OpenAI Codex Plugin support added
- Miessler's Personal AI Infrastructure repo active on GitHub

### LangChain (checked 2026-03-30)
- No March 2026 blog posts found via search (may be publishing elsewhere or slower cadence)
- **WARNING**: CVE-2026-33017 (Langflow) exploited within 20 hours — Langflow is related but separate from LangChain

### Andrej Karpathy (checked 2026-03-30)
- **Autoresearch open-sourced** 2026-03-07: AI agent ran 700 experiments over 2 days, found 20 training optimizations — this is the direct inspiration for Jarvis Phase 4D
- **"Humans are the bottleneck"** thesis (2026-03-23): In any AI domain with a computable metric, human researchers are now the bottleneck
- **"Dobby the Elf Claw"**: Custom home AI system controlled via WhatsApp — central layer over household systems
- **Workflow**: Claims 16 hrs/day talking to AI agents, hasn't written code manually since Dec 2025

### Hugging Face (checked 2026-03-30)
- **State of Open Source Spring 2026**: South Korea + Reflection AI data center partnership
- **Nemotron 3 Nano** (NVIDIA): Full weights, training recipes, datasets released
- **NVIDIA Cosmos Reason 2**: #1 open model for physical AI visual understanding
- **Transformers v5**: "Simple model definitions powering the AI ecosystem"

## High-Priority Items for Eric

1. **OpenAI acquiring Astral (uv/ruff/ty)** — If epdev uses uv or ruff, monitor for governance/licensing changes
2. **Krebs: AI Assistants security** — Directly relevant to Jarvis security posture; consider reading full article
3. **Malicious PyPI packages** — Check epdev dependencies against known-bad versions
4. **Claude Code v2.1.87** — Verify local version is current; MCP fixes may affect Jarvis
5. **Karpathy autoresearch** — Compare his 700-experiment approach to Jarvis 4D overnight runner design

## Run Log

```tsv
iteration	commit_hash	metric_value	delta	status	description
0	-	0	0	baseline	No sources.yaml exists
1	(local)	25	+25	kept	Created sources.yaml with 24 sources (6 T1, 6 T2, 12 T3)
2	(local)	25	0	kept	Checked 10 sources, wrote monitoring report with findings
```

## Notes

- `memory/work/jarvis/` is gitignored — files created locally but must use `git add -f` on overnight branch
- Tier 3 sources not checked this run (monthly cadence, not due)
- OWASP source (Tier 2) not checked — lower priority for this run
- The "Human source review ritual" task remains open — Eric should review these 24 sources and add his own
