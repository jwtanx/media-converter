@echo off
REM Install dependencies without pip version-check telemetry
set PIP_DISABLE_PIP_VERSION_CHECK=1
set PIP_NO_PYTHON_VERSION_WARNING=1
call .venv\Scripts\activate.bat
pip install --no-input -r requirements.txt
echo.
echo Done. Only yt-dlp is installed (no extra analytics packages).
