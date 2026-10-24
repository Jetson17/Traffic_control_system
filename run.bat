@echo off
title Traffic Signal Control System
echo ============================================================
echo   Traffic Signal Control System
echo   Intelligent Traffic Monitoring & Analysis
echo ============================================================
echo.
echo Launching local server at http://127.0.0.1:5000 ...
echo.
start http://127.0.0.1:5000
.\.venv\Scripts\python.exe app.py
pause
