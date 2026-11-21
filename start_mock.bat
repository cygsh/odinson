@echo off
:: Odinson - Demo / Mock Launcher (no Arduino needed)
set PYTHON=C:\Users\yoges\AppData\Local\Programs\Python\Python312\python.exe
cd /d c:\Users\yoges\Desktop\odinson
echo Starting Odinson in MOCK mode...
echo Open http://localhost:5000 in your browser
echo Press Ctrl+C to stop.
echo.
%PYTHON% run.py --mock --no-plot
