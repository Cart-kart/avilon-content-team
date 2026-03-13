@echo off
title avilonROBOTICS Dashboard
echo.
echo  ╔══════════════════════════════════════╗
echo  ║   avilonROBOTICS Content Dashboard   ║
echo  ╚══════════════════════════════════════╝
echo.

:: Kill any existing server on port 5050
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5050 "') do (
    taskkill /PID %%a /F >nul 2>&1
)

:: Start the server
echo  Starting dashboard server...
start "" /B python "D:\Claude Agent\dashboard\server.py"

:: Wait a moment for server to start
timeout /t 3 /nobreak >nul

:: Open in browser
echo  Opening dashboard in browser...
start http://localhost:5050

echo.
echo  Dashboard running at: http://localhost:5050
echo  Press any key to stop the server...
pause >nul

:: Stop server on exit
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5050 "') do (
    taskkill /PID %%a /F >nul 2>&1
)
echo  Server stopped.
