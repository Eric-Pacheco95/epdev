@echo off
REM Jarvis-MemorySampler -- Task Scheduler wrapper (2-min night / 10-min day).
REM Invokes memory_sampler.py to append one JSONL tick to
REM data/logs/memory_timeseries.jsonl. Success gate for memory-observability
REM PRD-2 Phase 1 (FR-001 / FR-003).

cd /d "C:\Users\ericp\Github\epdev"

if not exist "data\logs" mkdir "data\logs"

"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\memory_sampler.py
