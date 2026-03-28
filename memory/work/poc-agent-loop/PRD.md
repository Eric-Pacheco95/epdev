# PRD: Agent Definition Upgrade Script

## Purpose
Build a Python script that validates agent definition files against the Six-Section anatomy (Identity, Mission, Critical Rules, Deliverables, Workflow, Success Metrics). This is both a useful tool AND the test subject for the /implement-prd loop POC.

## Context
- Agent definitions live in `orchestration/agents/*.md`
- The Six-Section anatomy requires: Identity, Mission, Critical Rules, Deliverables, Workflow, Success Metrics
- Currently 5 agents, only Engineer has been upgraded to the new format
- Script should be reusable for future agent additions

## ISC

- [x] Script exists at `tools/scripts/validate_agents.py` and is executable via `python tools/scripts/validate_agents.py` | Verify: `python tools/scripts/validate_agents.py --help` exits 0 [E][M]
- [x] Script reads all `.md` files from `orchestration/agents/` directory | Verify: `python tools/scripts/validate_agents.py` outputs at least 5 agent names [E][M]
- [x] Script checks each agent file for all 6 required sections (Identity, Mission, Critical Rules, Deliverables, Workflow, Success Metrics) | Verify: run against Engineer.md (upgraded) = 6/6, run against Architect.md (old format) = less than 6/6 [E][M]
- [x] Script outputs a summary table: agent name, sections found, sections missing, score (N/6) | Verify: output contains a formatted table with all 5 agents [E][M]
- [x] Script exits with code 0 if all agents pass, code 1 if any agent has missing sections | Verify: `echo $?` after running shows appropriate exit code [E][M]
- [x] Script uses ASCII-only output (no Unicode box drawing) per CLAUDE.md steering rule | Verify: `python tools/scripts/validate_agents.py 2>&1 | grep -cP "[^\x00-\x7F]"` returns 0 [E][M]
