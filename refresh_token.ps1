$ErrorActionPreference = 'Continue'
# 桃园社区 token 续期：本脚本必须管理员运行
# 流程：解析真实IP -> 劫持hosts -> MITM反向代理 -> 强制微信小程序重连 -> 抓 /v1/wx/login -> 写回 config.json -> 还原
$Root = 'D:\ty_scan'
$log  = Join-Path $Root 'refresh.log'
function W($m) { $t = "$(Get-Date -Format 'HH:mm:ss') $m"; Write-Host $t; Add-Content -Path $log -Value $t -Encoding UTF8 }

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    W "!! 需要管理员权限"
    exit 1
}

W "=== refresh start ==="

# 1) 先解析真实 IP（必须在改 hosts 之前）
$ip = (Resolve-DnsName 'olwxbbs.sanguosha.com' -Type A -EA SilentlyContinue |
       Where-Object { $_.IPAddress } | Select-Object -First 1 -ExpandProperty IPAddress)
if (-not $ip) { W "!! 解析失败"; exit 2 }
W "upstream IP = $ip"

# 2) 劫持 hosts
$h = 'C:\Windows\System32\drivers\etc\hosts'
$orig = Get-Content $h -Raw -Encoding UTF8
if ($orig -notmatch 'olwxbbs\.sanguosha\.com') {
    Add-Content -Path $h -Value "`r`n# ty3-begin`r`n127.0.0.1 olwxbbs.sanguosha.com`r`n::1 olwxbbs.sanguosha.com`r`n# ty3-end" -Encoding UTF8
    W "hosts patched"
}
ipconfig /flushdns | Out-Null

# 3) 起 mitmproxy
$py3 = 'C:\Users\Administrator\AppData\Local\Programs\Python\Python313\Scripts\mitmdump.exe'
if (-not (Test-Path $py3)) { $py3 = 'C:\Users\Administrator\AppData\Local\Python\pythoncore-3.14-64\Scripts\mitmdump.exe' }
Get-NetTCPConnection -LocalPort 443 -State Listen -EA SilentlyContinue | ForEach-Object { try { Stop-Process -Id $_.OwningProcess -Force } catch {} }
Start-Sleep -Seconds 1
Remove-Item (Join-Path $Root 'clock.jsonl') -EA SilentlyContinue
$p = Start-Process -FilePath $py3 -ArgumentList @(
    '--mode', "reverse:https://${ip}:443@443",
    '--listen-host','::','--listen-port','443',
    '--set','ssl_insecure=true','--set','connection_strategy=lazy',
    '-s', (Join-Path $Root 'sni.py'),
    '-w', (Join-Path $Root 'clock.flows'), '--set','flow_detail=3'
) -PassThru -WindowStyle Minimized -RedirectStandardOutput (Join-Path $Root 'mitm_r_out.log') -RedirectStandardError (Join-Path $Root 'mitm_r_err.log')
W "mitmdump pid=$($p.Id)"
Start-Sleep -Seconds 6
if (-not (Get-NetTCPConnection -LocalPort 443 -State Listen -EA SilentlyContinue)) { W "!! 443 未监听"; exit 3 }

# 4) 强制小程序重连
$n = 0
Get-Process WeChatAppEx -EA SilentlyContinue | ForEach-Object { try { Stop-Process -Id $_.Id -Force; $n++ } catch {} }
W "killed WeChatAppEx x$n —— 请把桃园小程序重新打开（进任意页面即可）"

# 5) 等待 login 响应
$jsonl = Join-Path $Root 'clock.jsonl'
$picker = Join-Path $Root 'pick_token.py'
$pyExe = (Get-Command python -EA SilentlyContinue).Source
if (-not $pyExe) { $pyExe = (Get-Command py -EA SilentlyContinue).Source }
if (-not $pyExe) { $pyExe = 'python' }
$deadline = (Get-Date).AddSeconds(180)
$token = $null
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 3
    if (Test-Path $jsonl) {
        # 用 python 解析 jsonl：响应体里的引号被 json 转义过，正则扫原文匹配不到
        $out = & $pyExe $picker 2>$null
        if ($out) { $out = ($out | Out-String).Trim() }
        if ($out -and $out.StartsWith('eyJ')) { $token = $out; break }
    }
}

# 6) 还原
$cur = Get-Content $h -Raw -Encoding UTF8
$cur = [regex]::Replace($cur, '(?ms)\r?\n?# ty3-begin.*?# ty3-end', '')
Set-Content -Path $h -Value $cur.TrimEnd() -Encoding UTF8 -NoNewline
ipconfig /flushdns | Out-Null
Get-NetTCPConnection -LocalPort 443 -State Listen -EA SilentlyContinue | ForEach-Object { try { Stop-Process -Id $_.OwningProcess -Force } catch {} }
W "环境已还原"

if (-not $token) { W "!! 180 秒内没抓到 /v1/wx/login，token 未更新"; exit 4 }

# 7) 写回 config.json
$cfgPath = Join-Path $Root 'config.json'
$old = Get-Content $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json
$payload = $token.Split('.')[1]
$payload = $payload.Replace('-','+').Replace('_','/')
switch ($payload.Length % 4) { 2 { $payload += '==' } 3 { $payload += '=' } }
$j = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($payload)) | ConvertFrom-Json
$cfg = [ordered]@{
    token = $token
    uid = $j.sub
    exp = $j.exp
    captured_at = (Get-Date -Format 'yyyy-MM-ddTHH:mm:sszzz')
}
$cfg | ConvertTo-Json | Set-Content -Path $cfgPath -Encoding UTF8
$leftDays = [math]::Round(([double]$j.exp - [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) / 86400, 1)
W "[+] token 已更新 uid=$($j.sub) 剩余 $leftDays 天"
W "=== refresh done ==="