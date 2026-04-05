# DEPRECATED

> **This skill is deprecated.** Replaced by `/absorb` for external content analysis and `#jarvis-voice` (via `slack_voice_processor.py`) for voice dictation processing.
>
> - For external URLs (articles, videos, posts): use `/absorb <url> --quick|--normal|--deep`
> - For voice dumps and thought dictation: post to `#jarvis-voice` on Slack
> - For Notion Inbox: use `/notion-sync inbox`
>
> See PRD: `memory/work/absorb/PRD.md`


# DISCOVERY

## One-liner
DEPRECATED -- voice/audio capture (use /absorb or #jarvis-voice Slack instead)

## Stage
DEPRECATED

## Syntax
/voice-capture  # DEPRECATED -- use /absorb <url> or post to #jarvis-voice

## Parameters
- None (deprecated)

## Examples
- /absorb <url> --quick       # for external URLs/articles
- Post to #jarvis-voice       # for voice dictation / thought dumps
- /notion-sync inbox          # for Notion Inbox items

## Chains
- Replaced by: /absorb (external content), #jarvis-voice Slack channel (voice dictation)

## Output Contract
- DEPRECATED -- no output; route voice/audio work through /absorb or #jarvis-voice
