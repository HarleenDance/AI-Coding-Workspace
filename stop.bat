@echo off
title AI Coding Workspace - Stop Services

echo Stopping services...

REM Stop backend (python/uvicorn on port 8000)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /pid %%a /f >nul 2>&1 && echo   -^> Backend stopped
)

REM Stop frontend (node/vite on port 5173)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /pid %%a /f >nul 2>&1 && echo   -^> Frontend stopped
)

echo Done.
timeout /t 2 /nobreak >nul
