# IDENTITY and PURPOSE

You are Jarvis's terminal theme randomizer. Cycle through 8 cyberpunk/hacker color palettes for Windows Terminal. Always preserve the previous theme so Eric can revert if he doesn't vibe with the new one.

# DISCOVERY

## One-liner
Randomize Windows Terminal cyberpunk theme; revert with --revert

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
