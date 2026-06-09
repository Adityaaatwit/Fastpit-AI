@echo off
cd /d "%~dp0"
echo.
echo ========================================
echo   FAST PIT AI  (not PitLane)
echo   Folder: %CD%
echo ========================================
echo.

REM Stop anything still bound to old/default Streamlit ports
for %%P in (8501 8502) do (
  for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%P " ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
  )
)

echo Starting on http://localhost:8502  (port 8502 only)
echo Close ALL other localhost tabs, then open that URL.
echo.
python -m streamlit run run.py --server.port 8502
pause
