@echo off
cd /d "%~dp0"
set /p NICHO=Nicho (ex.: barbearia, pizzaria, academia):
set /p CIDADE=Cidade ou regiao (ex.: Ceilandia, DF):
.venv\Scripts\python.exe prospectar.py "%NICHO%" "%CIDADE%"
pause
