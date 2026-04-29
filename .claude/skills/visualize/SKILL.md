---
name: visualize
description: Generate Mermaid diagrams from complex inputs -- projects, workflows, brain structure, investigations
---

# IDENTITY and PURPOSE

Jarvis systems visualizer. Turn complex inputs (project relationships, dependency maps, workflow flows, architecture) into clear Mermaid diagrams exposing key structure and connections.

# DISCOVERY

## Stage
BUILD

## Syntax
/visualize <input>
/visualize <type> <input>
/visualize <input> --no-html

## Parameters
- type (optional, default: auto): brain | workflow | project | investigate | system | auto
- input: Content to visualize -- project relationships, workflow descriptions, research findings, system architecture (required)
- --no-html: Skip standalone HTML file generation and browser auto-open

## Examples
- /visualize brain -- generate Jarvis Brain node map (TELOS pillars, projects, skills, signals)
- /visualize workflow "skill pipeline from /project-init to /implement-prd"
- /visualize project crypto-bot -- project dependency and phase map
- /visualize system "Jarvis architecture: hooks, MCP, skills, memory"
- /visualize investigate memory/learning/synthesis/latest.md --no-html

## Chains
- Before: /project-init (for project diagrams), /research (for investigation visualizations), /deep-audit (for system architecture)
- After: Save to memory/work/{project}/ or orchestration/workflows/ (after approval)
- Related: /create-keynote (diagrams can feed presentations)
- Full: /deep-audit > /visualize system > /create-keynote (if presenting findings)

## Output Contract
- Input: Content or topic + optional type flag
- Output: Markdown with embedded Mermaid diagram, ANALYSIS (8-10 bullets), CONCLUSION, GAPS, Next Action
- Side effects: HTML viewer file generated and auto-opened in browser (unless --no-html), diagram saved to relevant directory after approval

## autonomous_safe
false

# STEPS

## Step 0: INPUT CHECK

- No input: print DISCOVERY block, STOP
- Invalid `<type>` (not brain/workflow/project/investigate/system/auto): print valid types, STOP
- --no-html present alongside bare /visualize (no input): invalid combination, print usage and STOP
- If input is a file path: confirm the file exists before proceeding (`ls <path>`); if missing, STOP with `File not found: <path>`

## Step 1: UNDERSTAND INPUT

1. **Fully understand the input** — read it completely before starting the diagram.

2. **Identify the visualization type** based on input or explicit argument:
   - `brain` — Jarvis Brain node map (TELOS pillars, projects, skills, signals as nodes; dependencies as edges)
   - `workflow` — skill pipeline or workflow sequence diagram
   - `project` — project dependency and phase map
   - `investigate` — investigation/research findings with evidence chains
   - `system` — system architecture (services, data flows, integrations)
   - `auto` — infer the best type from the input (default)

3. **Map all entities** — nodes, relationships, directionality, cardinality. Spend virtual time ensuring nothing is missed.

4. **Choose the right Mermaid diagram type**:
   - Node relationships → `graph TD` or `graph LR`
   - Sequences/workflows → `sequenceDiagram`
   - Phases/timelines → `gantt`
   - State machines → `stateDiagram-v2`
   - Entity relationships → `erDiagram`

5. **Design the diagram**:
   - Use node shapes to distinguish types (rectangles = processes, rounded = states, diamonds = decisions, cylinders = data stores)
   - Use edge labels to name relationships (not just arrows)
   - Use subgraphs to group related nodes
   - Color-code by category using Mermaid `style` or `classDef`

6. **Write ANALYSIS** — 8–10 bullet points of 16 words each covering the most important structural insights.

7. **Write CONCLUSION** — a single 25-word assessment of the most important takeaway from the visualization.

8. **Write GAPS** — 3–5 bullets identifying what's missing, unclear, or needs further mapping.

# OUTPUT FORMAT

```markdown
## Visualization: {title}

**Type**: {brain | workflow | project | investigate | system}
**Generated**: {YYYY-MM-DD}

### Diagram

```mermaid
{diagram here}
```

### ANALYSIS

- {bullet 1 — 16 words max}
- {bullet 2}
- ...up to 10 bullets

### CONCLUSION

{Single 25-word statement of the most important structural insight.}

### GAPS

- {what's missing or unclear}
- ...3–5 bullets

### Next Action

{One concrete next step: refine diagram, fill a gap, route to a skill}
```

# JARVIS INTEGRATION

- If type is `brain` → this feeds Phase 3D brain spec. Save output to `memory/work/brain_spec/` (create if needed).
- If type is `workflow` → save to `orchestration/workflows/` if Eric approves.
- If type is `project` → save to `memory/work/{project}/` after approval.
- Always propose saving — never auto-save without approval.

# OUTPUT INSTRUCTIONS

- Output Markdown with embedded Mermaid
- Diagrams must be syntactically valid Mermaid; make edge labels explicit (not just arrows)
- Dense enough to be useful, sparse enough to be readable
- **HTML viewer** (default, skip with `--no-html`): write standalone HTML file with Mermaid source in `<pre class="mermaid">` block, CDN script tag, noscript fallback, minimal centered styling; save to same dir as markdown output; auto-open with `start <file>` on Windows; use temp path if save dir undetermined


# INPUT

Visualize the following input. If a type argument is provided (brain/workflow/project/investigate/system), use it. Otherwise infer from context.

INPUT:

# VERIFY

- Mermaid diagram is syntactically valid (no unclosed brackets, valid node types, valid edge syntax) | Verify: Read diagram — scan for unclosed `[`, `(`, `{`; verify all edge arrows use valid syntax
- All edge labels have explicit verbs or subjects (no bare arrows with no label) | Verify: Read diagram edges — each `-->` must have a label
- HTML viewer file was generated and saved (unless --no-html was passed) | Verify: `ls data/visualizations/*.html` confirms file exists
- Auto-open was attempted on Windows | Verify: Read session output for start command or equivalent auto-open attempt
- No syntax errors remain in final diagram | Verify: Re-scan diagram after any fix

# LEARN

- Write a signal to memory/learning/signals/{YYYY-MM-DD}_visualize-{slug}.md when a visualization reveals a structural insight about Jarvis architecture that was not obvious from the code or docs (e.g., missing link in a flow, unexpected coupling, critical path)
- Rating: 7+ for architectural insights; 4-6 for documentation value only; skip signal for simple one-off diagrams with no reuse value
- If a diagram type (sequence, ER, flowchart) requires >2 iterations to pass syntax validation, note it: indicates the Mermaid syntax reference for that type needs an inline example added to STEPS
- If the same architecture component appears as an island (no edges) across 2+ independent diagrams, it is a dead or orphaned component — flag for `/quality-gate` review
