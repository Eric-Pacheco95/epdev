# Orchestration System

Multi-project management with named agents, workflows, and unified task tracking.

## Agents — `orchestration/agents/`

Named agent definitions with specific roles, tools, and behavioral rules.
See individual agent `.md` files for definitions.

Available agents:
- **Architect** — System design, planning, trade-off analysis
- **Engineer** — Implementation, code generation, debugging
- **SecurityAnalyst** — Threat modeling, vulnerability assessment, defensive testing
- **QATester** — Test creation, verification, self-heal validation
- **Orchestrator** — Project management, inflow/outflow tracking, reporting

## Workflows — `orchestration/workflows/`

Multi-step task chains that coordinate agents.

Format: YAML workflow definitions
```yaml
name: {workflow-name}
description: {what it does}
triggers: {manual|schedule|event}
steps:
  - agent: {agent-name}
    action: {what to do}
    inputs: {from previous step or static}
    outputs: {what to pass forward}
```

## Task Console — `orchestration/tasklist.md`

Unified view of all active tasks across all projects.

## Inflows & Outflows

Every project tracks:
- **Inflows**: What feeds into this project (data sources, dependencies, triggers)
- **Outflows**: What this project produces (artifacts, reports, APIs, notifications)
- **Status**: {planning|active|blocked|review|complete}
- **Health**: {green|yellow|red} based on ISC progress
