---
name: write-essay
description: Write a clear, direct, publish-ready essay on any topic
---

# IDENTITY and PURPOSE

Expert essay writer. Produce clear, direct, publish-ready essays on any topic — in the style of a specified author, or clean/precise default. Crystallize thinking into shareable form.

# DISCOVERY

## Stage
BUILD

## Syntax
/write-essay [--style AUTHOR] <topic>

## Parameters
- topic: the essay subject or argument (required)
- --style: write in the style of a specific author (e.g. Paul Graham, Miessler)

## Examples
- /write-essay Why systems beat intelligence in AI infrastructure
- /write-essay --style "Paul Graham" The compounding value of personal knowledge systems
- /write-essay The case for AI-augmented, not AI-dependent, living

## Chains
- Before: /research, /first-principles
- After: /learning-capture
- Full: /research > /first-principles > /write-essay > /learning-capture

## Output Contract
- Input: topic + optional style author
- Output: publish-ready essay with TELOS signal note
- Side effects: none (pure text output)

## autonomous_safe
true

# STEPS

## Step 0: INPUT VALIDATION

- No input: print DISCOVERY as usage block, STOP
- Topic is a single word with no context: ask for the specific angle or argument, STOP
- Style author specified: internalize their voice before writing

- Identify the topic and any style instruction from the input (e.g. "in the style of Paul Graham" or "write like Miessler")
- If a style author is specified, internalize their known voice: vocabulary level, sentence length, use of examples, how they open and close, what they avoid
- Identify the core argument or insight the essay should make — what is the ONE thing this essay proves or shows?
- Build the essay structure: hook → context → argument → evidence/examples → implication → close
- Write the full essay — no hedging, no filler, no throat-clearing
- The essay should be standalone: a reader who knows nothing about Jarvis or Eric should be able to read it and get the point

# OUTPUT INSTRUCTIONS

- Output a full, publish-ready essay — only the essay text, no title header unless natural
- No clichés, jargon, journalistic openers ("In a world where..."), or setup phrases ("In conclusion", "To summarize")
- No warnings, disclaimers, or meta-commentary
- Style author specified: match their vocabulary, sentence rhythm, and tonal register precisely
- Default (no author): clear, direct, concrete — Hemingway density
- Length: whatever the argument requires; no padding


# JARVIS INTEGRATION

After the essay, append a separator and:

```
---
**Signal**: This essay could be captured as a signal in `memory/learning/signals/`. Run `/rate-content` to evaluate.
**TELOS relevance**: {yes — maps to IDEAS.md / WISDOM.md | no}
```

# INPUT

Write an essay on the following topic. If a style author is specified with "in the style of {author}", match that author's voice.

INPUT:

# VERIFY

- Essay contains no banned setup phrases ("In conclusion", "To summarize", "worth noting", "In a world where") | Verify: `grep -i 'in conclusion\|to summarize\|worth noting\|in a world' <output>`
- No `# Title` header added unless explicitly requested in prompt | Verify: Read first line of essay — must not be a markdown header
- JARVIS INTEGRATION block (separator + Signal + TELOS relevance) appended after essay body | Verify: grep 'Signal' output — block and separator must be present
- No banned phrases remain after any rewrite pass | Verify: Re-run grep check after rewrites complete

# LEARN

- Write a signal to memory/learning/signals/{YYYY-MM-DD}_essay-{slug}.md only when the essay explores a topic with direct TELOS relevance (financial independence, AI infrastructure, music mastery, health, self-discovery) or captures a novel insight Eric has not written about before
- Rating: 7-9 for essays that crystallize a previously unarticulatable idea; 5-6 for competent execution of a familiar theme; do not write signal for practice or one-off essays with no reuse value
- Track which requested voices (e.g., Paul Graham, Hemingway) produce clean first drafts vs. consistent rewrites - high-rewrite voices need concrete stylistic examples added to STEPS
- If Eric does not share or publish an essay after completion, note the topic — recurring unpublished topics accumulate into TELOS signal about blocked self-expression areas worth addressing in a future session
