@echo off
REM Jarvis Signal Compression — runs monthly, 1st at 3:20 AM
REM Gzips processed signals older than 180 days

cd /d C:\Users\ericp\Github\epdev
C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe tools\scripts\compress_signals.py --execute >> data\logs\signal_compression.log 2>&1
