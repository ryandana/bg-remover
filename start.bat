@echo off
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Starting background remover server...
main.py
pause
