@echo off
REM Build a standalone Windows executable (run from project folder)
set PIP_DISABLE_PIP_VERSION_CHECK=1
set PIP_NO_PYTHON_VERSION_WARNING=1
call .venv\Scripts\activate.bat
pip install --no-input pyinstaller
pyinstaller --noconfirm --onefile --windowed --name "YouTubeDownloader" main.py
echo.
echo Executable: dist\YouTubeDownloader.exe
pause
