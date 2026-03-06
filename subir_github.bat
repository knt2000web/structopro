@echo off
echo ============================================
echo   Subiendo Diagrama NSR-10 a GitHub
echo ============================================

cd /d "%~dp0"

echo.
echo [1/5] Inicializando repositorio git...
git init

echo.
echo [2/5] Agregando todos los archivos...
git add .

echo.
echo [3/5] Creando el primer commit...
git commit -m "feat: Diagrama de Interaccion NSR-10 - version inicial"

echo.
echo [4/5] Configurando rama principal...
git branch -M main

echo.
echo [5/5] Conectando con GitHub y subiendo...
git remote add origin https://github.com/knt2000web/diagrama-nsr10.git
git push -u origin main

echo.
echo ============================================
echo   Listo! Revisa: github.com/knt2000web/diagrama-nsr10
echo ============================================
pause
