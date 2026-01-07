@echo off
REM Video Creator App - Simple Launcher
REM Double-click this file to start the app

echo Starting Video Creator App...
echo.

REM Activate virtual environment and start Streamlit
call .venv\Scripts\activate.bat
streamlit run streamlit_app.py --server.headless true

REM If the app closes, press any key to close window
pause
