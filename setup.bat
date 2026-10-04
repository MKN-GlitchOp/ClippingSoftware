@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  where py >nul 2>nul
  if errorlevel 1 (
    echo Install Python 3.12 from python.org, including the Python launcher.
    pause
    exit /b 1
  )
  py -3.12 -m venv .venv
)
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
if errorlevel 1 goto fail
where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo FFmpeg is missing. Install it using the README steps and reopen this window.
  goto fail
)
call npm.cmd --prefix frontend ci
if errorlevel 1 goto fail
call npm.cmd --prefix frontend run build
if errorlevel 1 goto fail
echo Setup complete. Launch start.bat.
pause
exit /b 0
:fail
echo Setup failed. Review the message above.
pause
exit /b 1
