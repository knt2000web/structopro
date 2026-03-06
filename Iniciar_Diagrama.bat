@echo off
echo ==========================================================
echo    INICIANDO PROGRAMA NSR-10 CON STREAMLIT               
echo ==========================================================
echo.
echo 1. Buscando Python y Streamlit...

:: Verificar si python está en el PATH
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] No se pudo encontrar Python. Asegurate de que este instalado.
    pause
    exit /b
)

:: Verificar si streamlit existe
python -m streamlit version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ADVERTENCIA] Streamlit no se reconoce comando. Intentando instalar librerias...
    python -m pip install streamlit matplotlib pandas numpy
)

echo 2. Iniciando el servidor local en el puerto 8502...
echo    (Deberia abrirse una pestana en tu navegador automaticamente)
echo.
echo Presiona CTRL+C en esta ventana cuando quieras apagar el programa.
echo ----------------------------------------------------------

:: Ejecutar streamlit y pausar en caso de fallo para ver el error
python -m streamlit run "%~dp0app.py" --server.port 8502
if %errorlevel% neq 0 (
    echo.
    echo [ERROR CRITICO] El programa se cerro inesperadamente. Revisa el error arriba.
    pause
)
