@echo off
title bishe - business mode
echo ==================================================
echo   BiShe Rescue  -  One-Click Business Mode
echo ==================================================
echo.

if not exist "%~dp0cloudflared-windows-amd64.exe" (
    echo [X] ERROR: cloudflared-windows-amd64.exe not found in this folder.
    echo.
    echo     1. Download it with your browser from the official link:
    echo        https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
    echo     2. Move the downloaded exe into this folder ^("D:\bishe"^)
    echo     3. Run this bat again.
    echo.
    pause
    exit /b 1
)

python -m streamlit version >nul 2>&1
if errorlevel 1 (
    echo [X] ERROR: streamlit not installed. Run this first:  pip install -r requirements.txt
    pause
    exit /b 1
)

echo [1/2] Starting local app on port 8501 ...
start "bishe-app" /min cmd /c "cd /d %~dp0 && python -m streamlit run app.py --server.headless true --server.port 8501"
timeout /t 6 /nobreak >nul

echo [2/2] Opening public tunnel ...
echo.
echo   ============================================
echo   YOUR SHOP URL will appear below, like:
echo   https://random-words.trycloudflare.com
echo   ------------------------------------------
echo   Close this window = shop closed.
echo   Do NOT run this bat twice at the same time.
echo   ============================================
echo.
"%~dp0cloudflared-windows-amd64.exe" tunnel --url http://localhost:8501
pause
