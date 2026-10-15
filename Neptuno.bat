@echo off
REM ============================================================
REM  Aparthotel Neptuno Costa Adeje - Revenue Dashboard
REM  1) Procesa el buzon (Excel-Lunes\BUZON)
REM  2) Abre el dashboard en el navegador (puerto 8502)
REM ============================================================
cd /d "%~dp0"
call .venv\Scripts\activate.bat
set PYTHONIOENCODING=utf-8

echo.
echo === Procesando buzon Aparthotel Neptuno ===
python scripts\procesar_buzon.py
echo.
echo === Abriendo dashboard Aparthotel Neptuno ===
start "" "http://localhost:8502"
streamlit run app.py --server.port 8502
