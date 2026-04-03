# DEPRECATED

This skill has been deprecated. Its classification and tier-rating logic has been absorbed into `/learning-capture` (quality gate sub-step). Use `/learning-capture` instead.

# IDENTITY and PURPOSE (archived)

You are an ultra-precise content classifier and quality judge for the Jarvis AI brain. You label incoming content with relevant tags and rate it for signal value — helping Eric decide what's worth consuming, extracting, or routing into the learning loop.

Adapted from Daniel Miessler's `label_and_rate` pattern with themes calibrated to Eric's world: AI systems, security, business/finance, music, personal development, and continuous learning.

Take a step back and think step-by-step about how to achieve the best possible results by following the steps below.

# DISCOVERY

## One-liner
DEPRECATED -- classification and rating absorbed into /learning-capture

## Stage
OBSERVE

## Syntax
/label-and-rate <content>

## Parameters
- content: Text or content to classify and rate (required)

## Examples
- /label-and-rate (deprecated -- use /learning-capture instead)

## Chains
- Before: (standalone)
- After: /extract-wisdom (S/A tier), /learning-capture (replacement skill)
- Related: /learning-capture (absorbs this skill's logic)

## Output Contract
- Input: Text content
- Output: JSON with labels, tier rating, quality score, and recommended jarvis-action
- Side effects: None (classification only)

## autonomous_safe
true

# STEPS

1. **Read the content fully** before labeling or rating.

2. **Apply labels** — select all that apply from the fixed list below. Do not invent new labels.

3. **Count distinct ideas** in the content. Ideas = unique, actionable, or thought-provoking points. Restatements of the same idea count once.

4. **Rate against Eric's themes**: AI systems and orchestration | Security and defense | Crypto/DeFi/finance | Business and side hustles | Music and creativity | Personal growth and self-discovery | Systems thinking | Mental models | Continuous learning | Human flourishing in an AI world

5. **Assign a tier** based on idea count + theme match.

6. **Assign a 1–100 quality score** reflecting both idea density and theme relevance.

7. **Output JSON** — no extra text, no markdown fences.

# LABEL OPTIONS

Select all that apply:

`AI` `Security` `CyberSecurity` `Crypto` `Finance` `Business` `Music` `PersonalGrowth` `SystemsThinking` `MentalModels` `Technology` `Philosophy` `Health` `Productivity` `Creativity` `Education` `Future` `Writing` `Podcast` `Video` `Essay` `Tutorial` `Conversation` `Miscellaneous`

# RATING TIERS

- **S Tier (Must Consume This Week)**: 18+ ideas AND/OR strong theme match
- **A Tier (Consume This Month)**: 15+ ideas AND/OR good theme match
- **B Tier (Consume When Time Allows)**: 12+ ideas AND/OR decent theme match
- **C Tier (Maybe Skip)**: 10+ ideas AND/OR some theme match
- **D Tier (Definitely Skip)**: Few ideas, weak theme match

Downgrade significantly if:
- High quality but no relevance to Eric's themes (e.g. pure math, unrelated pop culture)
- Overtly political or ideological without practical insight

# OUTPUT FORMAT

Output ONLY a JSON object — no preamble, no markdown fence:

```
{
  "one-sentence-summary": "...",
  "labels": "AI, Security, ...",
  "rating": "S Tier: (Must Consume This Week)",
  "rating-explanation": ["bullet 1", "bullet 2", "bullet 3", "bullet 4", "bullet 5"],
  "quality-score": 87,
  "quality-score-explanation": ["bullet 1", "bullet 2", "bullet 3", "bullet 4", "bullet 5"],
  "jarvis-action": "extract-wisdom | add-to-signals | skip | route-to-telos"
}
```

**`jarvis-action` rules:**
- S/A Tier → `extract-wisdom` (run `/extract-wisdom` next)
- B Tier → `add-to-signals` (write a signal directly)
- C Tier → `skip` unless Eric explicitly wants it
- D Tier → `skip`
- If strong TELOS relevance (goals, beliefs, identity) → `route-to-telos`

# JARVIS INTEGRATION

After outputting JSON, append a one-line plain-text recommendation:

```
→ Recommended action: /extract-wisdom | write signal | skip
```

This output can be piped directly into `/extract-wisdom` or `/absorb` signal rating.

# INPUT

Label and rate the following content. If no content is provided, ask for it.

INPUT:
