@echo off
echo Starting Bedrock Pi 5 update from Windows...

REM Check for WSL
where wsl >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo WSL not found. Trying Git Bash...
    where bash >nul 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo Neither WSL nor Git Bash found. Please install one of them.
        pause
        exit /b 1
    )
    bash update_bedrock_pi5.sh
) else (
    wsl ./update_bedrock_pi5.sh
)

pause
