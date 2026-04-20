@echo off
REM Invokes Moralis stream monitor using crypto-bot's venv.
REM Registered as hourly Windows Task Scheduler job (see register_moralis_monitor_task.ps1).
cd /d C:\Users\ericp\Github\crypto-bot
call .venv\Scripts\python.exe tools\moralis_stream_monitor.py
