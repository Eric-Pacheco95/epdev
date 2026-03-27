# Signal: OneDrive iOS Files provider is architecturally read-only
- Date: 2026-03-26
- Rating: 8
- Category: insight
- Source: session
- Observation: iOS Shortcuts "Append to Text File" action cannot write to OneDrive even when the OneDrive app is installed on iPhone. The OneDrive iOS Files provider extension is read-only by design for third-party app access — this is an architectural limitation, not a permissions setting.
- Implication: iCloud Drive (via iCloud for Windows on desktop) is the correct transport for iOS Shortcut → desktop file sync. Any future design that requires mobile → desktop file write should default to iCloud, not OneDrive. Do not attempt to guide Eric through OneDrive permissions fixes for this — it won't work.
- Context: Building 3C-3 iOS Shortcut voice capture pipeline. Spent ~30 min discovering this after OneDrive app was installed on iPhone and PAI Voice shortcut was built.
