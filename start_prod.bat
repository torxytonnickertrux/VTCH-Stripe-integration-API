@echo off
echo Iniciando servidor em modo de PRODUCAO (Waitress)...
echo Pressione CTRL+C para parar.
echo.
waitress-serve --port=4242 --call wsgi:app