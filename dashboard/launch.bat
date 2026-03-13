@echo off
echo Starting avilonROBOTICS Content Dashboard...

:: Start Flask dashboard
start /B python3 "D:\Claude Agent\dashboard\server.py"
timeout /t 3 /nobreak >nul

:: Start Cloudflare tunnel
start /B "" "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:5050 2> "D:\Claude Agent\reports\tunnel-err.log"
timeout /t 8 /nobreak >nul

:: Extract and show public URL
echo.
echo ========================================
echo   Local:  http://localhost:5050
for /f "tokens=*" %%a in ('findstr "trycloudflare.com" "D:\Claude Agent\reports\tunnel-err.log"') do (
    echo   Online: %%a
)
echo ========================================
echo.
start http://localhost:5050
pause
