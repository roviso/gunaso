@echo off
echo ====================================
echo   Gunaso UI - Starting Dev Server
echo ====================================
echo.
echo Installing dependencies...
call npm install
echo.
echo Starting dev server on http://localhost:3000
echo.
call npm run dev
pause
