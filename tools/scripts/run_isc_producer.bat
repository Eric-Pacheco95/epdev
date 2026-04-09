@echo off
REM Jarvis ISC Producer — runs daily at 2:00 AM
REM Scans all active PRDs, runs isc_executor.py, produces batch report

cd /d C:\Users\ericp\Github\epdev
C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe tools\scripts\isc_producer.py --verbose >> data\logs\isc_producer.log 2>&1
