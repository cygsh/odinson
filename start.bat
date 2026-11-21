@echo off
:: Odinson - Quick Launcher
:: Run from the project root: start.bat [--mock] [--no-plot]

set PYTHON=C:\Users\yoges\AppData\Local\Programs\Python\Python312\python.exe
set PROJECT=c:\Users\yoges\Desktop\odinson

cd /d %PROJECT%

echo.
echo  ==============================================
echo   Odinson - IoT Vibration ^& Seismic Monitor
echo  ==============================================
echo.

if "%1"=="--mock" (
    echo  Running in MOCK mode (no hardware needed)
    echo  Open http://localhost:5000 in your browser
    echo.
    %PYTHON% run.py --mock --no-plot
) else (
    echo  Running in SERIAL mode (Arduino on COM3 expected)
    echo  Open http://localhost:5000 in your browser
    echo  Tip: run  start.bat --mock  for no-hardware demo
    echo.
    %PYTHON% run.py --no-plot
)
