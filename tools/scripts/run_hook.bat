@echo off
REM Shared hook launcher — resolves repo root and picks the best Python.
REM Usage: run_hook.bat <script-relative-to-repo-root> [args...]
setlocal
set "REPO_ROOT=%~dp0..\.."
pushd "%REPO_ROOT%" >nul
where py >nul 2>&1
if %ERRORLEVEL%==0 (
  py -3 "%~1" %2 %3 %4 %5 %6 %7 %8 %9
) else (
  python "%~1" %2 %3 %4 %5 %6 %7 %8 %9
)
set "RC=%ERRORLEVEL%"
popd >nul
exit /b %RC%
