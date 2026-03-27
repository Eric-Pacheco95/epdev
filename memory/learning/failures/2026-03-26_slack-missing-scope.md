# Failure: Slack bot missing chat:write scope
- Date: 2026-03-26
- Severity: 4
- Context: Running hook smoke-test via slack_notify.py to verify Stop hook Slack integration. Token was set correctly as system env var.
- Root Cause: The ClaudeActivities Slack app was missing the chat:write (and/or chat:write.public) OAuth scope. Token authenticated successfully but API returned "missing_scope" error.
- Fix Applied: Added chat:write scope to the Slack app's OAuth settings and reinstalled the app to the workspace. Smoke-test then returned exit 0 with no errors — message delivered to #epdev.
- Prevention: When creating or reconfiguring a Slack bot, always verify OAuth scopes include chat:write before testing. Add a scope checklist to EPDEV_JARVIS_BIBLE.md under Slack setup.
- Steering Rule: When smoke-testing Slack notify, a "missing_scope" error always means the bot app needs OAuth scope additions + reinstall — not a token or code issue.
