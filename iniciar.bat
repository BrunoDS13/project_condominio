@echo off
setlocal
cd /d "%~dp0"
title Gestao de Condominio

if not exist venv\Scripts\python.exe (
    echo Criando ambiente virtual...
    python -m venv venv || goto :erro
    venv\Scripts\python -m pip install -q -r requirements.txt || goto :erro
)
if not exist .env copy .env.example .env >nul

set FLASK_APP=wsgi.py
echo Aplicando migrations...
venv\Scripts\flask db upgrade || goto :erro

start "" /b cmd /c "timeout /t 3 >nul & start http://127.0.0.1:5000"
echo.
echo Servidor em http://127.0.0.1:5000  (Ctrl+C para parar)
venv\Scripts\flask run
goto :eof

:erro
echo.
echo Ocorreu um erro. Veja a mensagem acima.
pause
