@echo off
echo ==========================================================
echo    INICIANDO PROGRAMA NSR-10 CON STREAMLIT               
echo ==========================================================
echo.
echo 1. Buscando Python 3.12...

:: Usar Python 3.12 directamente
set PYTHON="C:\Users\cagch\AppData\Local\Programs\Python\Python312\python.exe"

:: Verificar que Python 3.12 exista
if not exist %PYTHON% (
    echo [ERROR] No se encontro Python 3.12 en la ruta esperada.
    echo         Instala Python 3.12 desde https://www.python.org/downloads/
    pause
    exit /b
)

%PYTHON% --version

:: Verificar si streamlit existe
%PYTHON% -m streamlit version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ADVERTENCIA] Streamlit no encontrado. Instalando dependencias...
    %PYTHON% -m pip install streamlit matplotlib pandas "numpy<2.0" ifcopenshell
)

echo 2. Iniciando el servidor local en el puerto 8502...
echo    (Deberia abrirse una pestana en tu navegador automaticamente)
echo.
echo Presiona CTRL+C en esta ventana cuando quieras apagar el programa.
echo ----------------------------------------------------------

:: Ejecutar streamlit y pausar en caso de fallo para ver el error
%PYTHON% -m streamlit run "%~dp0Inicio_App.py" --server.port 8502
if %errorlevel% neq 0 (
    echo.
    echo [ERROR CRITICO] El programa se cerro inesperadamente. Revisa el error arriba.
    pause
)
