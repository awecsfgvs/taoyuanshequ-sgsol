@echo off
chcp 65001 >nul
REM 桃园社区 token 续期：需要管理员权限（会弹 UAC）
REM 流程：写 hosts -> 本地 mitmproxy 反代 443 -> 杀掉 WeChatAppEx 强制小程序重连 -> 抓 /v1/wx/login 里的 JWT -> 写回 config.json -> 还原 hosts
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','\"%~dp0refresh_token.ps1\"'"
echo 已请求管理员权限，UAC 点「是」后：
echo   1) 把微信里的三国杀OL/桃园小程序重新打开，随便进一个页面
echo   2) 等脚本抓包（最多 180 秒），成功后 config.json 会被自动更新
pause
