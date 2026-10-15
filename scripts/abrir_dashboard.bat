@echo off
REM Lanzador del dashboard Streamlit Neptuno Costa Adeje (puerto 8502).
cd /d "%~dp0.."
call .venv\Scripts\activate.bat
streamlit run app.py --server.port 8502
