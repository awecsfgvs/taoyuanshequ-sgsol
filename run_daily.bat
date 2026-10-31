@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo [!] 找不到 python，请先安装 Python 3.9+ 并加入 PATH
  exit /b 1
)
python "%~dp0taoyuan_daily.py" >> "%~dp0run_daily.out" 2>&1
exit /b %ERRORLEVEL%
