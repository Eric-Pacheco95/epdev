# Signal: 4-hour session limits mean Stop hook may not fire — capture before limit
- Date: 2026-03-26
- Rating: 7
- Category: improvement
- Source: session
- Observation: Eric regularly hits 4-hour/100% Claude Code session limits. When the session ends hard at the limit, the Stop hook (hook_stop.py) may not fire — meaning the Slack "session ended" digest and signal metadata update are skipped. The learning content is safe on disk, but the automated end-of-session ritual is lost.
- Implication: Run /learning-capture explicitly before approaching session limits — do not rely on Stop hook as the sole capture trigger. Treat it as a mid-session checkpoint ritual whenever the session has been productive, not just at natural end. "Capture early, capture often" is safer than "capture at the end."
- Context: Discussed during hook audit and workflow planning. Stop hook verified working for normal exits; hard limit exits are out of scope for hooks.
