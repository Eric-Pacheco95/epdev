@echo off
echo Rescheduling Jarvis overnight tasks...
echo.

schtasks /Change /TN "\Jarvis\Jarvis-SessionCleanup"           /ST 00:30 /RU ericp /RP "" && echo OK  SessionCleanup    00:30 || echo FAIL SessionCleanup
schtasks /Change /TN "\Jarvis\Jarvis-IndexUpdate"              /ST 01:00 /RU ericp /RP "" && echo OK  IndexUpdate        01:00 || echo FAIL IndexUpdate
schtasks /Change /TN "\Jarvis\JarvisEventRotation"             /ST 01:05 /RU ericp /RP "" && echo OK  EventRotation      01:05 || echo FAIL EventRotation
schtasks /Change /TN "\Jarvis\Jarvis-HeartbeatRotation"        /ST 01:10 /RU ericp /RP "" && echo OK  HeartbeatRotation  01:10 || echo FAIL HeartbeatRotation
schtasks /Change /TN "\Jarvis\Jarvis-SignalCompression"        /ST 01:15 /RU ericp /RP "" && echo OK  SignalCompression  01:15 || echo FAIL SignalCompression
schtasks /Change /TN "\Jarvis\Jarvis-ParadigmHealth"           /ST 04:00 /RU ericp /RP "" && echo OK  ParadigmHealth     04:00 || echo FAIL ParadigmHealth
schtasks /Change /TN "\Jarvis\Jarvis-Autoresearch-CodeQuality" /ST 04:45 /RU ericp /RP "" && echo OK  Autoresearch-CQ    04:45 || echo FAIL Autoresearch-CQ
schtasks /Change /TN "\Jarvis\Jarvis-TELOS-Introspection"      /ST 07:15 /RU ericp /RP "" && echo OK  TELOS-Introspection 07:15 || echo FAIL TELOS-Introspection
schtasks /Change /TN "\Jarvis\Jarvis-Security-Audit"           /ST 08:00 /RU ericp /RP "" && echo OK  Security-Audit     08:00 || echo FAIL Security-Audit

echo.
echo Done. Press any key to close.
pause
