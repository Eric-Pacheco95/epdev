TASK_FAILED: auto-heal-jarvis-dispatcher-20260426-070023
BLOCKER: CONSTRAINT VIOLATION -- security validator blocks autonomous writes to tools/scripts/

SITUATION:
1. The primary fix (_dispatcher_slot = None at top of _dispatch_one) is ALREADY PRESENT
   at line 2473 of tools/scripts/jarvis_dispatcher.py. No code change needed for that.

2. ISC verification (python tools/scripts/jarvis_dispatcher.py --test) exits code 1
   due to a pre-existing Test 27 failure (domain routing assertion). The assert checks
   "platform-specific.md" not in ctx_base, but autonomous-rules.md (always-injected)
   mentions the string in its text -- a false positive introduced after commit e257ab9
   added steering rules that reference platform-specific.md.

3. Fixing Test 27 requires editing tools/scripts/jarvis_dispatcher.py -- but the
   security validator (validate_tool_use.py) blocks ALL autonomous edits to tools/scripts/.

HUMAN DECISION NEEDED:
A) Accept the primary fix as already merged (the UnboundLocalError is resolved) and
   separately fix Test 27 in an interactive session.
B) Temporarily allow self-heal tasks to edit the specific file they are healing, then
   re-dispatch.
C) Fix Test 27 manually: change line ~3753 to check for the header pattern
   "--- orchestration/steering/platform-specific.md ---" instead of bare "platform-specific.md".
