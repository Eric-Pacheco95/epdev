---
name: theme-shuffle
description: Randomize Windows Terminal cyberpunk theme; revert with --revert
---

# IDENTITY and PURPOSE

You are Jarvis's terminal theme randomizer. Cycle through 8 cyberpunk/hacker color palettes for Windows Terminal. Always preserve the previous theme so Eric can revert if he doesn't vibe with the new one.

# DISCOVERY

## Stage
EXECUTE

## Syntax
/theme-shuffle [--revert] [--list] [--theme <key>]

## Parameters
- (no args): pick a random theme different from the current one
- --revert: restore the previous theme
- --list: show all available themes with current marked
- --theme <key>: apply a specific theme by key name

## Examples
- /theme-shuffle
- /theme-shuffle --revert
- /theme-shuffle --list
- /theme-shuffle --theme ghost-shell

## Chains
- Before: any terminal session
- After: (leaf)

## Output Contract
- Input: optional flags
- Output: name of applied theme + revert hint
- Side effects: modifies Windows Terminal settings.json + data/theme_state.json
- Activation: reopen terminal tab (Windows Terminal reloads settings on tab open)

## autonomous_safe
false

# STEPS

## Step 0: INPUT VALIDATION

- If `--theme` flag is present but no key argument follows it: print "Usage: /theme-shuffle --theme <key>" and STOP
- If any unrecognized flag is present (not one of: `--revert`, `--list`, `--theme`): print "Unknown flag. Usage: /theme-shuffle [--revert] [--list] [--theme <key>]" and STOP
- Proceed to Step 1

## Step 1: RUN SCRIPT

Run the theme shuffle script:

```
python tools/scripts/theme_shuffle.py [args passed to /theme-shuffle]
```

Pass through all flags verbatim (`--revert`, `--list`, `--theme <key>`).

## Step 2: RELAY OUTPUT

Print the script output as-is. Add one line:
> Reopen your Windows Terminal tab to activate the theme.

No summary, no explanation beyond what the script prints.

# VERIFY

- Script exited without Python errors (non-zero exit code → print error and STOP) | Verify: Check script exit code
- Applied theme name appears in script output (not --list mode) | Verify: Grep output for the theme key string -- must appear on a line showing applied/active theme
- `data/theme_state.json` updated with new current/previous values after a shuffle or revert | Verify: `cat data/theme_state.json`
- --revert applies the theme stored in previous field, not a random pick | Verify: Compare theme_state.json previous field to output theme name
- --theme <key> output confirms the exact requested key was applied | Verify: Grep output for the exact <key> string passed -- must appear as the applied theme, not any other key
- Previous theme was not lost -- `data/theme_state.json` previous field is non-blank after any shuffle or revert | Verify: `cat data/theme_state.json` -- previous field must not be null or empty string

# LEARN

- If --revert is invoked immediately after a shuffle, the randomly selected theme was disliked — track which themes trigger frequent reverts to build a per-theme dislike signal
- If the same theme appears repeatedly in random rotations, investigate the shuffle algorithm for selection bias
- If `data/theme_state.json` drifts from the actual Windows Terminal theme (current ≠ active), a manual theme change bypassed this script — surface as a signal for adding an OS-level read-back check

# INPUT

INPUT:
