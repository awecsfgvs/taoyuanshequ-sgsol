@echo off
chcp 65001 >nul
title 桃园 token 续期（免提权）
powershell -NoProfile -ExecutionPolicy Bypass -File "D:/ty_scan/grab_and_apply.ps1"
echo.
pause
