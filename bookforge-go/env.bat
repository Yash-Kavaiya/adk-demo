@echo off
REM BookForge Go Environment Variables
REM Load environment variables from .env file

if not exist .env (
    echo Error: .env file not found
    echo Please copy .env.example to .env and configure it
    exit /b 1
)

for /f "tokens=1,2 delims==" %%a in (.env) do (
    if not "%%a"=="" (
        if not "%%a"=="#" (
            set %%a=%%b
            echo Loaded: %%a
        )
    )
)

echo.
echo Environment variables loaded successfully
echo To run the agent:
echo   go run agent.go
echo Or to run web interface:
echo   go run agent.go web api webui
