@echo off
cd /d %~dp0
if not exist .venv (
  echo Creating virtual environment with Python 3.11...
  py -3.11 -m venv .venv || goto :err
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  pip install -r requirements.txt || goto :err
) else (
  call .venv\Scripts\activate.bat
)
echo.
echo  Six Strings is starting:  http://localhost:8000
echo.
start "" http://localhost:8000
python -m uvicorn app:app --port 8000
goto :eof
:err
echo Setup failed - see the message above.
pause
