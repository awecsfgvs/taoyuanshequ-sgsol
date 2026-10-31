@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
python "%~dp0taoyuan_claim.py" %* >> "%~dp0claim.out" 2>&1
exit /b %ERRORLEVEL%
