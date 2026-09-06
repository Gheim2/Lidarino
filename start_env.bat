@echo off
if not defined JAZZY_WS (
    echo ERROR: JAZZY_WS not set. Create a .env file from .env.example
    pause & exit /b 1
)
echo Starting environment in %JAZZY_WS%...
cd /d "%JAZZY_WS%"
start "Zenoh Router" powershell -NoExit -Command "pixi run zenoh"
timeout /t 3 /nobreak >nul
start "Isaac Sim" powershell -NoExit -Command "pixi run sim"
start "ROS2 Terminal" powershell -NoExit -Command "pixi shell"