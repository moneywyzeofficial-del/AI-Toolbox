@echo off
title AI Toolbox
chcp 65001 > nul

echo ========================================================
echo               AI Toolbox - A Iniciar...
echo ========================================================
echo.

cd /d "%~dp0"

echo A verificar dependências...
python -m pip install -r backend\requirements.txt --quiet

echo.
echo ========================================================
echo  Aplicação disponível no PC: http://127.0.0.1:8000
echo  Para ligar no iPhone: abre o botão "Ligar ao iPhone"
echo ========================================================
echo.

timeout /t 1 /nobreak > nul

start "" "http://127.0.0.1:8000"

python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

pause
