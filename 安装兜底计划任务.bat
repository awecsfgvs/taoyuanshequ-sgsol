@echo off
chcp 65001 >nul
REM 给桃园日常注册 Windows 兜底计划任务（需要管理员，会弹 UAC）
REM 只在你想「即使 DSH 没开也要跑」时执行一次；DSH cron 是主跑，脚本自带当日去重，不会重复点赞
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','D:\ty_scan\register_task.ps1'"
echo 已请求管理员权限。UAC 窗口点「是」后，稍等几秒看任务是否注册成功：
echo    schtasks /Query /TN TaoyuanCheckin
pause