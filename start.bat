@echo off
title AI Coding Workspace Launcher

set ROOT=%~dp0
set BACKEND=%ROOT%aI-coding-workspace-backend\
set FRONTEND=%ROOT%aI-coding-workspace-frontend\
set PYTHON=D:\Roaming\pyenv-win\pyenv-win\versions\3.12.0\python.exe

echo ========================================
echo   AI Coding Workspace - Start Services
echo ========================================
echo.

REM 1. Check database
echo [1/3] Checking database container...
docker ps --filter name=pgvector-db --format "{{.Status}}" 2>nul | findstr "Up" >nul
if %errorlevel%==0 (
    echo   -^> pgvector container is running
) else (
    echo   -^> Starting pgvector container...
    docker start pgvector-db >nul 2>&1
    if %errorlevel%==0 (
        echo   -^> pgvector container started
        timeout /t 3 /nobreak >nul
    ) else (
        echo   -^> [ERROR] Run manually:
        echo      docker run --name pgvector-db -e POSTGRES_PASSWORD=123456 -p 5433:5432 -d pgvector/pgvector:pg18
        pause
        exit /b 1
    )
)

REM 2. Start backend
echo [2/3] Starting backend (port 8000)...
start "Backend - uvicorn" /D "%BACKEND%" "%PYTHON%" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

REM 3. Start frontend
echo [3/3] Starting frontend (port 5173)...
timeout /t 2 /nobreak >nul
start "Frontend - vite" /D "%FRONTEND%" cmd /c "npm run dev -- --host 0.0.0.0 & pause"

echo.
echo ========================================
echo   All services started!
echo ========================================
echo.
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000/docs
echo.
echo   Run stop.bat to stop all services
echo.
pause
