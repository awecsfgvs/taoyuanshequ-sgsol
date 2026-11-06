@echo off
chcp 65001 >nul
REM 桃园社区 token 续期（需管理员：改 hosts + 占 443）
REM 双击本文件 -> UAC 点“是” -> 微信里重新打开三国杀OL/桃园小程序任意页面
setlocal
echo 正在申请管理员权限...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath powershell -Verb RunAs -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-NoLogo','-NoExit','-File','D:/ty_scan/refresh_token.ps1'"
if errorlevel 1 (
  echo.
  echo [X] 提权失败或被取消。请右键本文件 - 以管理员身份运行。
)
echo.
echo 提权窗口已打开：保持可见，按提示在微信里重新打开桃园小程序。
echo 抓完后回来跑: python D:/ty_scan/check_health.py
pause
